from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, cast

from chiwawa_backend.errors import ConfigurationError
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.photo_times import photo_time_columns

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable

    from chiwawa_backend.config import Settings
    from chiwawa_backend.services.memorial_photo_repository import NewPhotoRecord
    from chiwawa_backend.services.upload_admission import UploadLease


def insert_photo_with_lease(
    settings: Settings,
    photo: NewPhotoRecord,
    lease: UploadLease,
    active_at: Callable[[], str],
) -> int:
    if photo.user_id != lease.user_id or photo.size_bytes != lease.reserved_bytes:
        message = "photo does not match upload lease"
        raise ConfigurationError(message)
    with contextlib.closing(connect(settings)) as connection, connection:
        _ = connection.execute("BEGIN IMMEDIATE")
        _require_active_lease(connection, lease, active_at())
        photo_id = _insert_photo(connection, photo)
    if photo_id is None:
        message = "failed to persist memorial photo"
        raise ConfigurationError(message)
    return photo_id


def _require_active_lease(
    connection: sqlite3.Connection,
    lease: UploadLease,
    active_at: str,
) -> None:
    row = cast(
        "sqlite3.Row | None",
        connection.execute(
            """
            SELECT lease_id FROM upload_leases
            WHERE lease_id = ? AND user_id = ? AND reserved_bytes = ?
              AND expires_at > ?
            """,
            (lease.lease_id, lease.user_id, lease.reserved_bytes, active_at),
        ).fetchone(),
    )
    if row is None:
        message = "upload lease is no longer active"
        raise ConfigurationError(message)


def _insert_photo(
    connection: sqlite3.Connection,
    photo: NewPhotoRecord,
) -> int | None:
    taken_at, taken_at_utc, local_date = photo_time_columns(photo.taken_at)
    cursor = connection.execute(
        """
        INSERT INTO memorial_photos (
            user_id, file_name, stored_path, content_type, taken_at,
            latitude, longitude, address, memo, created_at,
            taken_at_utc, local_date, size_bytes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            photo.user_id,
            photo.file_name,
            photo.stored_path,
            photo.content_type,
            taken_at.isoformat(),
            photo.latitude,
            photo.longitude,
            photo.address,
            photo.memo,
            photo.created_at.isoformat(),
            taken_at_utc,
            local_date,
            photo.size_bytes,
        ),
    )
    return cursor.lastrowid
