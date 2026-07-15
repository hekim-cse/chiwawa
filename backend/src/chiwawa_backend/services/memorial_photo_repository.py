from __future__ import annotations

import contextlib
import datetime as dt
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from chiwawa_backend.errors import ConfigurationError, NotFoundError
from chiwawa_backend.schemas.memorial import MemorialPhotoItem
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.photo_times import (
    normalize_photo_time,
    photo_month_bounds,
    photo_time_columns,
    utc_sort_instant,
)

if TYPE_CHECKING:
    import sqlite3

    from chiwawa_backend.config import Settings


@dataclass(frozen=True, slots=True)
class PhotoRecord:
    id: int
    user_id: int
    file_name: str
    stored_path: str
    content_type: str
    taken_at: dt.datetime
    latitude: float | None
    longitude: float | None
    address: str | None
    memo: str | None
    created_at: dt.datetime
    size_bytes: int


@dataclass(frozen=True, slots=True)
class NewPhotoRecord:
    user_id: int
    file_name: str
    stored_path: str
    content_type: str
    taken_at: dt.datetime
    latitude: float | None
    longitude: float | None
    address: str | None
    memo: str | None
    created_at: dt.datetime
    size_bytes: int


@dataclass(frozen=True, slots=True)
class PhotoUpdate:
    taken_at: dt.datetime
    latitude: float | None
    longitude: float | None
    address: str | None
    memo: str | None


def require_photo(settings: Settings, user_id: int, photo_id: int) -> PhotoRecord:
    with contextlib.closing(connect(settings)) as connection:
        return require_photo_on(connection, user_id, photo_id)


def require_photo_on(
    connection: sqlite3.Connection,
    user_id: int,
    photo_id: int,
) -> PhotoRecord:
    row = cast(
        "sqlite3.Row | None",
        connection.execute(
            "SELECT * FROM memorial_photos WHERE id = ? AND user_id = ?",
            (photo_id, user_id),
        ).fetchone(),
    )
    if row is None:
        raise NotFoundError(entity="memorial_photo", entity_id=str(photo_id))
    return _record(row)


def normalize_storage(
    settings: Settings,
    record: PhotoRecord,
    relative_path: str,
    size_bytes: int,
) -> PhotoRecord:
    if record.stored_path == relative_path and record.size_bytes == size_bytes:
        return record
    with contextlib.closing(connect(settings)) as connection, connection:
        _ = connection.execute(
            """
            UPDATE memorial_photos SET stored_path = ?, size_bytes = ?
            WHERE id = ? AND user_id = ?
            """,
            (relative_path, size_bytes, record.id, record.user_id),
        )
    return replace(record, stored_path=relative_path, size_bytes=size_bytes)


def month_counts(
    settings: Settings,
    user_id: int,
    month_prefix: str,
) -> list[tuple[dt.date, int]]:
    month_start, month_end = photo_month_bounds(month_prefix)
    with contextlib.closing(connect(settings)) as connection:
        rows = cast(
            "list[sqlite3.Row]",
            connection.execute(
                """
                SELECT local_date AS day, COUNT(*) AS photo_count
                FROM memorial_photos
                WHERE user_id = ? AND local_date >= ? AND local_date < ?
                GROUP BY day ORDER BY day
                """,
                (user_id, month_start, month_end),
            ).fetchall(),
        )
    return [
        (dt.date.fromisoformat(_text(row, "day")), _int(row, "photo_count"))
        for row in rows
    ]


def day_photos(
    settings: Settings,
    user_id: int,
    day: dt.date,
) -> list[PhotoRecord]:
    with contextlib.closing(connect(settings)) as connection:
        rows = cast(
            "list[sqlite3.Row]",
            connection.execute(
                """
                SELECT * FROM memorial_photos
                WHERE user_id = ? AND local_date = ?
                """,
                (user_id, day.isoformat()),
            ).fetchall(),
        )
    ordered_rows = sorted(
        rows,
        key=lambda row: (utc_sort_instant(_text(row, "taken_at_utc")), _int(row, "id")),
    )
    return [_record(row) for row in ordered_rows]


def update_photo(
    connection: sqlite3.Connection,
    user_id: int,
    photo_id: int,
    update: PhotoUpdate,
) -> None:
    taken_at, taken_at_utc, local_date = photo_time_columns(update.taken_at)
    _ = connection.execute(
        """
        UPDATE memorial_photos
        SET taken_at = ?, latitude = ?, longitude = ?, address = ?, memo = ?,
            taken_at_utc = ?, local_date = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            taken_at.isoformat(),
            update.latitude,
            update.longitude,
            update.address,
            update.memo,
            taken_at_utc,
            local_date,
            photo_id,
            user_id,
        ),
    )


def item_from_record(record: PhotoRecord) -> MemorialPhotoItem:
    return MemorialPhotoItem(
        id=record.id,
        file_name=record.file_name,
        content_type=record.content_type,
        taken_at=record.taken_at,
        latitude=record.latitude,
        longitude=record.longitude,
        address=record.address,
        memo=record.memo,
        file_url=f"/api/v1/memorial/photos/{record.id}/file",
        created_at=record.created_at,
    )


def _record(row: sqlite3.Row) -> PhotoRecord:
    return PhotoRecord(
        id=_int(row, "id"),
        user_id=_int(row, "user_id"),
        file_name=_text(row, "file_name"),
        stored_path=_text(row, "stored_path"),
        content_type=_text(row, "content_type"),
        taken_at=normalize_photo_time(
            dt.datetime.fromisoformat(_text(row, "taken_at")),
        ),
        latitude=_optional_float(row, "latitude"),
        longitude=_optional_float(row, "longitude"),
        address=_optional_text(row, "address"),
        memo=_optional_text(row, "memo"),
        created_at=dt.datetime.fromisoformat(_text(row, "created_at")),
        size_bytes=_int(row, "size_bytes"),
    )


def _column(row: sqlite3.Row, key: str) -> str | int | float | None:
    return cast("str | int | float | None", row[key])


def _text(row: sqlite3.Row, key: str) -> str:
    value = _column(row, key)
    if not isinstance(value, str):
        message = f"column {key} must be text"
        raise ConfigurationError(message)
    return value


def _optional_text(row: sqlite3.Row, key: str) -> str | None:
    value = _column(row, key)
    if value is None or isinstance(value, str):
        return value
    message = f"column {key} must be text or null"
    raise ConfigurationError(message)


def _int(row: sqlite3.Row, key: str) -> int:
    value = _column(row, key)
    if not isinstance(value, int):
        message = f"column {key} must be an integer"
        raise ConfigurationError(message)
    return value


def _optional_float(row: sqlite3.Row, key: str) -> float | None:
    value = _column(row, key)
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    message = f"column {key} must be numeric or null"
    raise ConfigurationError(message)
