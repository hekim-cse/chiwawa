from __future__ import annotations

import contextlib
import datetime as dt
import os
import sqlite3
import time
from typing import TYPE_CHECKING, cast

from chiwawa_backend.services.database import connect
from chiwawa_backend.services.memorial_photo_repository import (
    NewPhotoRecord,
    day_photos,
    month_counts,
    require_photo,
)
from chiwawa_backend.services.photo_times import current_photo_time, photo_time_columns
from tests.memorial_test_support import insert_user, settings

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.config import Settings


def _new_photo(
    user_id: int,
    file_name: str,
    taken_at: dt.datetime,
) -> NewPhotoRecord:
    return NewPhotoRecord(
        user_id=user_id,
        file_name=file_name,
        stored_path=f"{user_id}/{file_name}",
        content_type="image/jpeg",
        taken_at=taken_at,
        latitude=None,
        longitude=None,
        address=None,
        memo=None,
        created_at=dt.datetime(2026, 7, 1, tzinfo=dt.UTC),
        size_bytes=1,
    )


def _insert_photo(settings: Settings, photo: NewPhotoRecord) -> int:
    taken_at, taken_at_utc, local_date = photo_time_columns(photo.taken_at)
    with contextlib.closing(connect(settings)) as connection, connection:
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
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def _time_columns(db_path: Path, photo_id: int) -> tuple[str, str, str]:
    with contextlib.closing(sqlite3.connect(db_path)) as connection:
        row = cast(
            "tuple[str, str, str] | None",
            connection.execute(
                """
                SELECT taken_at, taken_at_utc, local_date
                FROM memorial_photos WHERE id = ?
                """,
                (photo_id,),
            ).fetchone(),
        )
    assert row is not None
    return row


def test_naive_photo_time_is_interpreted_in_tokyo(tmp_path: Path) -> None:
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)

    photo_id = _insert_photo(
        active_settings,
        _new_photo(
            user_id,
            "naive.jpg",
            dt.datetime.fromisoformat("2026-07-01T12:00:00"),
        ),
    )

    record = require_photo(active_settings, user_id, photo_id)
    assert record.taken_at.isoformat() == "2026-07-01T12:00:00+09:00"
    assert _time_columns(active_settings.auth_db_path(), photo_id) == (
        "2026-07-01T12:00:00+09:00",
        "2026-07-01T03:00:00+00:00",
        "2026-07-01",
    )


def test_aware_photo_time_uses_tokyo_calendar_date(tmp_path: Path) -> None:
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    source_zone = dt.timezone(dt.timedelta(hours=-5))

    photo_id = _insert_photo(
        active_settings,
        _new_photo(
            user_id,
            "boundary.jpg",
            dt.datetime(2026, 7, 1, 18, 30, tzinfo=source_zone),
        ),
    )

    record = require_photo(active_settings, user_id, photo_id)
    assert record.taken_at.isoformat() == "2026-07-02T08:30:00+09:00"
    assert month_counts(active_settings, user_id, "2026-07") == [
        (dt.date(2026, 7, 2), 1)
    ]


def test_timeline_orders_mixed_offsets_by_utc_instant(tmp_path: Path) -> None:
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    early_id = _insert_photo(
        active_settings,
        _new_photo(
            user_id,
            "early.jpg",
            dt.datetime(
                2026,
                7,
                2,
                8,
                tzinfo=dt.timezone(dt.timedelta(hours=9)),
            ),
        ),
    )
    with contextlib.closing(connect(active_settings)) as connection, connection:
        _ = connection.execute(
            "UPDATE memorial_photos SET taken_at_utc = ? WHERE id = ?",
            ("2026-07-01T23:00:00.000Z", early_id),
        )
    same_instant_id = _insert_photo(
        active_settings,
        _new_photo(
            user_id,
            "same-instant.jpg",
            dt.datetime(2026, 7, 1, 23, tzinfo=dt.UTC),
        ),
    )
    late_id = _insert_photo(
        active_settings,
        _new_photo(
            user_id,
            "late.jpg",
            dt.datetime(
                2026,
                7,
                1,
                23,
                30,
                tzinfo=dt.timezone(dt.timedelta(hours=-5)),
            ),
        ),
    )

    records = day_photos(active_settings, user_id, dt.date(2026, 7, 2))
    assert [record.id for record in records] == [
        early_id,
        same_instant_id,
        late_id,
    ]


def test_fallback_time_is_independent_of_host_timezone() -> None:
    original_tz = os.environ.get("TZ")
    try:
        os.environ["TZ"] = "UTC"
        time.tzset()

        observed = current_photo_time()

        assert observed.utcoffset() == dt.timedelta(hours=9)
    finally:
        if original_tz is None:
            _ = os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original_tz
        time.tzset()


def test_day_query_uses_persisted_time_columns(tmp_path: Path) -> None:
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    with contextlib.closing(connect(active_settings)) as connection, connection:
        cursor = connection.execute(
            """
            INSERT INTO memorial_photos (
                user_id, file_name, stored_path, content_type, taken_at,
                created_at, taken_at_utc, local_date, size_bytes
            ) VALUES (?, 'legacy.jpg', ?, 'image/jpeg',
                      '1999-01-01T00:00:00+09:00',
                      '2026-07-02T00:00:00+00:00',
                      '2026-07-01T23:00:00+00:00', '2026-07-02', 1)
            """,
            (user_id, f"{user_id}/legacy.jpg"),
        )
        photo_id = cursor.lastrowid
    assert photo_id is not None

    records = day_photos(active_settings, user_id, dt.date(2026, 7, 2))

    assert [record.id for record in records] == [photo_id]
