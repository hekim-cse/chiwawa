"""회원 단위 memorial 사진 저장/조회 서비스.

사진 파일은 MEMORIAL_PHOTO_DIR(기본 backend/data/memorial_photos)에 저장하고,
메타데이터는 memorial_photos 테이블(google_users 외래키)에 저장한다.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import os
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from fastapi import HTTPException, status

from chiwawa_backend.errors import ConfigurationError, NotFoundError
from chiwawa_backend.schemas.memorial import (
    MemorialCalendarDay,
    MemorialCalendarResponse,
    MemorialDayResponse,
    MemorialPhotoItem,
    MemorialPhotoPatchRequest,
    MemorialTimelineEntry,
)
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.exif import InvalidImageError, read_exif, validate_image
from chiwawa_backend.services.geocode import reverse_geocode


@dataclass(frozen=True, slots=True)
class PhotoUpload:
    file_name: str
    content_type: str
    data: bytes
    taken_at: dt.datetime | None
    latitude: float | None
    longitude: float | None
    memo: str | None


def save_photo(user_id: int, upload: PhotoUpload) -> MemorialPhotoItem:
    if not upload.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="only image uploads are supported",
        )
    try:
        validate_image(upload.data)
    except InvalidImageError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="uploaded file is not a valid image",
        ) from error
    exif = read_exif(upload.data)
    taken_at = upload.taken_at or exif.taken_at or _now_utc()
    latitude = upload.latitude if upload.latitude is not None else exif.latitude
    longitude = upload.longitude if upload.longitude is not None else exif.longitude
    address = _resolve_address(latitude, longitude)
    stored = _store_file(user_id, upload.file_name, upload.data)
    try:
        with contextlib.closing(connect()) as connection, connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO memorial_photos (
                        user_id, file_name, stored_path, content_type,
                        taken_at, latitude, longitude, address, memo, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        upload.file_name,
                        str(stored),
                        upload.content_type,
                        taken_at.isoformat(),
                        latitude,
                        longitude,
                        address,
                        upload.memo,
                        _now_utc().isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="unknown user",
                ) from error
            photo_id = cursor.lastrowid
    except (ConfigurationError, HTTPException, OSError, sqlite3.Error):
        with contextlib.suppress(OSError):
            stored.unlink(missing_ok=True)
        raise
    if photo_id is None:  # pragma: no cover
        message = "failed to persist memorial photo"
        raise RuntimeError(message)
    return get_photo(user_id, photo_id)


def month_calendar(user_id: int, year: int, month: int) -> MemorialCalendarResponse:
    month_prefix = f"{year:04d}-{month:02d}"
    with contextlib.closing(connect()) as connection:
        rows = cast(
            "list[sqlite3.Row]",
            connection.execute(
                """
            SELECT substr(taken_at, 1, 10) AS day, COUNT(*) AS photo_count
            FROM memorial_photos
            WHERE user_id = ? AND substr(taken_at, 1, 7) = ?
            GROUP BY day
            ORDER BY day
            """,
                (user_id, month_prefix),
            ).fetchall(),
        )
    days = [
        MemorialCalendarDay(
            day=dt.date.fromisoformat(_text(row, "day")),
            photo_count=_int(row, "photo_count"),
        )
        for row in rows
    ]
    return MemorialCalendarResponse(year=year, month=month, days=days)


def day_timeline(user_id: int, day: dt.date) -> MemorialDayResponse:
    with contextlib.closing(connect()) as connection:
        rows = cast(
            "list[sqlite3.Row]",
            connection.execute(
                """
                SELECT * FROM memorial_photos
                WHERE user_id = ? AND substr(taken_at, 1, 10) = ?
                ORDER BY taken_at, id
                """,
                (user_id, day.isoformat()),
            ).fetchall(),
        )
    items = [
        MemorialTimelineEntry(seq=seq, photo=_item_from_row(row))
        for seq, row in enumerate(rows)
    ]
    return MemorialDayResponse(day=day, items=items)


def get_photo(user_id: int, photo_id: int) -> MemorialPhotoItem:
    return _item_from_row(_require_row(user_id, photo_id))


def photo_file(user_id: int, photo_id: int) -> tuple[Path, str]:
    row = _require_row(user_id, photo_id)
    path = Path(_text(row, "stored_path"))
    if not path.is_file():
        raise NotFoundError(entity="memorial_photo_file", entity_id=str(photo_id))
    return path, _text(row, "content_type")


def update_photo(
    user_id: int,
    photo_id: int,
    patch: MemorialPhotoPatchRequest,
) -> MemorialPhotoItem:
    current = get_photo(user_id, photo_id)
    taken_at = patch.taken_at or current.taken_at
    latitude = patch.latitude if patch.latitude is not None else current.latitude
    longitude = patch.longitude if patch.longitude is not None else current.longitude
    memo = patch.memo if patch.memo is not None else current.memo
    moved = latitude != current.latitude or longitude != current.longitude
    address = _resolve_address(latitude, longitude) if moved else current.address
    with contextlib.closing(connect()) as connection, connection:
        _ = connection.execute(
            """
            UPDATE memorial_photos
            SET taken_at = ?, latitude = ?, longitude = ?, address = ?, memo = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                taken_at.isoformat(),
                latitude,
                longitude,
                address,
                memo,
                photo_id,
                user_id,
            ),
        )
    return get_photo(user_id, photo_id)


def delete_photo(user_id: int, photo_id: int) -> None:
    row = _require_row(user_id, photo_id)
    with contextlib.closing(connect()) as connection, connection:
        _ = connection.execute(
            "DELETE FROM memorial_photos WHERE id = ? AND user_id = ?",
            (photo_id, user_id),
        )
    Path(_text(row, "stored_path")).unlink(missing_ok=True)


def _resolve_address(latitude: float | None, longitude: float | None) -> str | None:
    if latitude is None or longitude is None:
        return None
    return reverse_geocode(latitude, longitude)


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


def _photo_dir() -> Path:
    configured = os.getenv("MEMORIAL_PHOTO_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[3] / "data" / "memorial_photos"


def _store_file(user_id: int, file_name: str, data: bytes) -> Path:
    suffix = Path(file_name).suffix.lower() or ".bin"
    target_dir = _photo_dir() / str(user_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid.uuid4().hex}{suffix}"
    _ = target.write_bytes(data)
    return target


def _require_row(user_id: int, photo_id: int) -> sqlite3.Row:
    with contextlib.closing(connect()) as connection:
        row = cast(
            "sqlite3.Row | None",
            connection.execute(
                "SELECT * FROM memorial_photos WHERE id = ? AND user_id = ?",
                (photo_id, user_id),
            ).fetchone(),
        )
    if row is None:
        raise NotFoundError(entity="memorial_photo", entity_id=str(photo_id))
    return row


def _item_from_row(row: sqlite3.Row) -> MemorialPhotoItem:
    photo_id = _int(row, "id")
    return MemorialPhotoItem(
        id=photo_id,
        file_name=_text(row, "file_name"),
        content_type=_text(row, "content_type"),
        taken_at=dt.datetime.fromisoformat(_text(row, "taken_at")),
        latitude=_optional_float(row, "latitude"),
        longitude=_optional_float(row, "longitude"),
        address=_optional_text(row, "address"),
        memo=_optional_text(row, "memo"),
        file_url=f"/api/v1/memorial/photos/{photo_id}/file",
        created_at=dt.datetime.fromisoformat(_text(row, "created_at")),
    )


def _column(row: sqlite3.Row, key: str) -> object:
    return cast("object", row[key])


def _text(row: sqlite3.Row, key: str) -> str:
    value = _column(row, key)
    if not isinstance(value, str):
        message = f"column {key} must be text"
        raise TypeError(message)
    return value


def _optional_text(row: sqlite3.Row, key: str) -> str | None:
    value = _column(row, key)
    if value is None or isinstance(value, str):
        return value
    message = f"column {key} must be text or null"
    raise TypeError(message)


def _int(row: sqlite3.Row, key: str) -> int:
    value = _column(row, key)
    if not isinstance(value, int):
        message = f"column {key} must be an integer"
        raise TypeError(message)
    return value


def _optional_float(row: sqlite3.Row, key: str) -> float | None:
    value = _column(row, key)
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    message = f"column {key} must be numeric or null"
    raise TypeError(message)
