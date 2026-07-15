from __future__ import annotations

import contextlib
import datetime as dt
import math
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from chiwawa_backend.errors import (
    ApplicationError,
    ConfigurationError,
    InsufficientStorageError,
    PayloadTooLargeError,
    RateLimitError,
)
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.local_photo_store import LocalPhotoStore
from chiwawa_backend.services.upload_admission_repository import (
    RATE_WINDOW,
    backfill_legacy_sizes,
    global_lease_usage,
    lease_usage,
    photo_usage,
    purge,
    rate_usage,
    record_attempt,
)
from chiwawa_backend.services.upload_lease_heartbeat import UploadLeaseHeartbeat

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from chiwawa_backend.config import Settings


@dataclass(frozen=True, slots=True)
class UploadLease:
    lease_id: str
    user_id: int
    reserved_bytes: int
    expires_at: dt.datetime


class UploadAdmission:
    def __init__(
        self,
        settings: Settings,
        *,
        store: LocalPhotoStore | None = None,
        clock: Callable[[], dt.datetime] | None = None,
        disk_free_bytes: Callable[[Path], int] | None = None,
        lease_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._settings: Settings = settings
        self._store: LocalPhotoStore = store or LocalPhotoStore(settings)
        self._clock: Callable[[], dt.datetime] = clock or (
            lambda: dt.datetime.now(dt.UTC)
        )
        self._disk_free_bytes: Callable[[Path], int] = (
            disk_free_bytes or _free_disk_bytes
        )
        self._lease_id_factory: Callable[[], str] = lease_id_factory or (
            lambda: uuid.uuid4().hex
        )

    def acquire(self, user_id: int, size_bytes: int) -> UploadLease:
        now = self._aware_now()
        expires_at = now + dt.timedelta(
            seconds=self._settings.upload_lease_ttl_seconds,
        )
        lease = UploadLease(
            lease_id=self._lease_id_factory(),
            user_id=user_id,
            reserved_bytes=size_bytes,
            expires_at=expires_at,
        )
        with contextlib.closing(connect(self._settings)) as connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            try:
                purge(connection, now)
                integrity_error = backfill_legacy_sizes(
                    connection,
                    self._store,
                    user_id,
                )
                record_attempt(connection, user_id, size_bytes, now)
                rejection = integrity_error or self._rejection(
                    connection,
                    user_id,
                    size_bytes,
                    now,
                )
                if rejection is None:
                    try:
                        _ = connection.execute(
                            """
                            INSERT INTO upload_leases (
                                lease_id, user_id, reserved_bytes,
                                acquired_at, expires_at
                            ) VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                lease.lease_id,
                                user_id,
                                size_bytes,
                                now.isoformat(),
                                expires_at.isoformat(),
                            ),
                        )
                    except sqlite3.IntegrityError as error:
                        message = "upload lease id collision"
                        raise ConfigurationError(message) from error
                connection.commit()
            except (ConfigurationError, sqlite3.Error, OSError):
                connection.rollback()
                raise
        if rejection is not None:
            raise rejection
        return lease

    def release(self, lease: UploadLease) -> None:
        with contextlib.closing(connect(self._settings)) as connection, connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            _ = connection.execute(
                "DELETE FROM upload_leases WHERE lease_id = ? AND user_id = ?",
                (lease.lease_id, lease.user_id),
            )

    def renew(self, lease: UploadLease) -> None:
        with contextlib.closing(connect(self._settings)) as connection, connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            now = self._aware_now()
            expires_at = now + dt.timedelta(
                seconds=self._settings.upload_lease_ttl_seconds,
            )
            cursor = connection.execute(
                """
                UPDATE upload_leases SET expires_at = ?
                WHERE lease_id = ? AND user_id = ? AND reserved_bytes = ?
                  AND expires_at > ?
                """,
                (
                    expires_at.isoformat(),
                    lease.lease_id,
                    lease.user_id,
                    lease.reserved_bytes,
                    now.isoformat(),
                ),
            )
        if cursor.rowcount != 1:
            message = "upload lease is no longer active"
            raise ConfigurationError(message)

    def heartbeat(self, lease: UploadLease) -> UploadLeaseHeartbeat:
        ttl = self._settings.upload_lease_ttl_seconds
        interval = min(max(ttl / 3, 0.05), 1.0)
        return UploadLeaseHeartbeat(lambda: self.renew(lease), interval)

    def active_at(self) -> str:
        return self._aware_now().isoformat()

    def _aware_now(self) -> dt.datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            message = "upload admission clock must be timezone-aware"
            raise ConfigurationError(message)
        return now.astimezone(dt.UTC)

    def _rejection(
        self,
        connection: sqlite3.Connection,
        user_id: int,
        size_bytes: int,
        now: dt.datetime,
    ) -> ApplicationError | None:
        settings = self._settings
        if size_bytes < 0 or size_bytes > settings.max_photo_bytes:
            return PayloadTooLargeError("photo file is too large")
        active_count, reserved_bytes = lease_usage(connection, user_id)
        global_count, global_reserved_bytes = global_lease_usage(connection)
        rejections = (
            self._quota_rejection(
                connection,
                user_id,
                size_bytes,
                active_count,
                reserved_bytes,
            ),
            self._rate_rejection(connection, user_id, now),
            self._concurrency_rejection(global_count, active_count),
            self._disk_rejection(size_bytes, global_reserved_bytes),
        )
        return next((error for error in rejections if error is not None), None)

    def _quota_rejection(
        self,
        connection: sqlite3.Connection,
        user_id: int,
        size_bytes: int,
        active_count: int,
        reserved_bytes: int,
    ) -> ApplicationError | None:
        photo_count, persisted_bytes = photo_usage(connection, user_id)
        if photo_count + active_count >= self._settings.max_photos_per_user:
            return PayloadTooLargeError("photo count quota exceeded")
        if (
            persisted_bytes + reserved_bytes + size_bytes
            > self._settings.max_photo_bytes_per_user
        ):
            return PayloadTooLargeError("photo byte quota exceeded")
        return None

    def _rate_rejection(
        self,
        connection: sqlite3.Connection,
        user_id: int,
        now: dt.datetime,
    ) -> ApplicationError | None:
        rate_count, newest = rate_usage(connection, user_id)
        if rate_count <= self._settings.max_uploads_per_user_per_hour:
            return None
        return RateLimitError(
            "upload rate limit exceeded",
            retry_after=_rate_retry_after(now, newest),
        )

    def _concurrency_rejection(
        self,
        global_count: int,
        active_count: int,
    ) -> ApplicationError | None:
        settings = self._settings
        if global_count >= settings.max_concurrent_uploads:
            detail = "global upload concurrency limit exceeded"
        elif active_count >= settings.max_concurrent_uploads_per_user:
            detail = "user upload concurrency limit exceeded"
        else:
            return None
        return RateLimitError(
            detail,
            retry_after=settings.upload_lease_ttl_seconds,
        )

    def _disk_rejection(
        self,
        size_bytes: int,
        global_reserved_bytes: int,
    ) -> ApplicationError | None:
        settings = self._settings
        free_bytes = self._disk_free_bytes(self._store.root)
        if (
            free_bytes - global_reserved_bytes - size_bytes
            >= settings.min_free_disk_bytes
        ):
            return None
        return InsufficientStorageError("insufficient local photo storage")


def _free_disk_bytes(path: Path) -> int:
    return shutil.disk_usage(path).free


def _rate_retry_after(now: dt.datetime, newest: str) -> int:
    try:
        newest_time = dt.datetime.fromisoformat(newest)
    except ValueError:
        return 3600
    return max(1, math.ceil((newest_time + RATE_WINDOW - now).total_seconds()))
