from __future__ import annotations

import contextlib
import datetime as dt
import sqlite3
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from chiwawa_backend.errors import (
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
)
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.upload_lease_heartbeat import UploadLeaseHeartbeat

if TYPE_CHECKING:
    from collections.abc import Callable

    from chiwawa_backend.config import Settings


@dataclass(frozen=True, slots=True)
class UploadRequestSlot:
    slot_id: str
    user_id: int


class UploadRequestAdmission:
    def __init__(
        self,
        settings: Settings,
        *,
        clock: Callable[[], dt.datetime] | None = None,
        slot_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._settings: Settings = settings
        self._clock: Callable[[], dt.datetime] = clock or (
            lambda: dt.datetime.now(dt.UTC)
        )
        self._slot_id_factory: Callable[[], str] = slot_id_factory or (
            lambda: uuid.uuid4().hex
        )

    def acquire(self, user_id: int) -> UploadRequestSlot:
        now = self._aware_now()
        expires_at = now + self._ttl()
        slot = UploadRequestSlot(self._slot_id_factory(), user_id)
        rejection: RateLimitError | None = None
        with contextlib.closing(connect(self._settings)) as connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            try:
                _ = connection.execute(
                    "DELETE FROM upload_request_slots WHERE expires_at <= ?",
                    (now.isoformat(),),
                )
                self._require_user(connection, user_id)
                global_count, user_count = self._usage(connection, user_id)
                rejection = self._rejection(global_count, user_count)
                if rejection is None:
                    _ = connection.execute(
                        """
                        INSERT INTO upload_request_slots (
                            slot_id, user_id, acquired_at, expires_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            slot.slot_id,
                            user_id,
                            now.isoformat(),
                            expires_at.isoformat(),
                        ),
                    )
                connection.commit()
            except (AuthenticationError, ConfigurationError, sqlite3.Error):
                connection.rollback()
                raise
        if rejection is not None:
            raise rejection
        return slot

    def renew(self, slot: UploadRequestSlot) -> None:
        now = self._aware_now()
        with contextlib.closing(connect(self._settings)) as connection, connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE upload_request_slots SET expires_at = ?
                WHERE slot_id = ? AND user_id = ? AND expires_at > ?
                """,
                (
                    (now + self._ttl()).isoformat(),
                    slot.slot_id,
                    slot.user_id,
                    now.isoformat(),
                ),
            )
        if cursor.rowcount != 1:
            message = "upload request slot is no longer active"
            raise ConfigurationError(message)

    def release(self, slot: UploadRequestSlot) -> None:
        with contextlib.closing(connect(self._settings)) as connection, connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            _ = connection.execute(
                "DELETE FROM upload_request_slots WHERE slot_id = ? AND user_id = ?",
                (slot.slot_id, slot.user_id),
            )

    def heartbeat(self, slot: UploadRequestSlot) -> UploadLeaseHeartbeat:
        ttl_seconds = self._settings.upload_lease_ttl_seconds
        interval = min(max(ttl_seconds / 3, 0.05), 1.0)
        return UploadLeaseHeartbeat(lambda: self.renew(slot), interval)

    def _aware_now(self) -> dt.datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            message = "upload request admission clock must be timezone-aware"
            raise ConfigurationError(message)
        return now.astimezone(dt.UTC)

    def _ttl(self) -> dt.timedelta:
        return dt.timedelta(seconds=self._settings.upload_lease_ttl_seconds)

    def _rejection(
        self,
        global_count: int,
        user_count: int,
    ) -> RateLimitError | None:
        if global_count >= self._settings.max_concurrent_uploads:
            detail = "global upload concurrency limit exceeded"
        elif user_count >= self._settings.max_concurrent_uploads_per_user:
            detail = "user upload concurrency limit exceeded"
        else:
            return None
        return RateLimitError(detail, retry_after=1)

    @staticmethod
    def _require_user(connection: sqlite3.Connection, user_id: int) -> None:
        row = cast(
            "sqlite3.Row | None",
            connection.execute(
                "SELECT 1 FROM google_users WHERE id = ?",
                (user_id,),
            ).fetchone(),
        )
        if row is None:
            message = "unknown user"
            raise AuthenticationError(message)

    @staticmethod
    def _usage(
        connection: sqlite3.Connection,
        user_id: int,
    ) -> tuple[int, int]:
        row = cast(
            "sqlite3.Row | None",
            connection.execute(
                """
                SELECT COUNT(*), COUNT(CASE WHEN user_id = ? THEN 1 END)
                FROM upload_request_slots
                """,
                (user_id,),
            ).fetchone(),
        )
        if row is None or not isinstance(row[0], int) or not isinstance(row[1], int):
            message = "invalid upload request slot usage"
            raise ConfigurationError(message)
        return row[0], row[1]
