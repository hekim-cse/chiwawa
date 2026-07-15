from __future__ import annotations

import contextlib
import datetime as dt
import io
from typing import TYPE_CHECKING

from PIL import Image
from pydantic import SecretStr

from chiwawa_backend.config import Settings
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.local_photo_store import LocalPhotoStore
from chiwawa_backend.services.upload_admission import UploadAdmission

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

NOW = dt.datetime(2026, 7, 14, 1, 2, 3, tzinfo=dt.UTC)


def _signing_material() -> str:
    return "test-only-secret-at-least-32-characters"


def settings(tmp_path: Path, **overrides: int) -> Settings:
    return Settings(
        google_auth_db_path=tmp_path / "app.db",
        memorial_photo_dir=tmp_path / "photos",
        jwt_secret=SecretStr(_signing_material()),
        min_free_disk_bytes=overrides.get("min_free_disk_bytes", 1),
        max_photo_bytes=overrides.get("max_photo_bytes", 100),
        max_photos_per_user=overrides.get("max_photos_per_user", 2),
        max_photo_bytes_per_user=overrides.get("max_photo_bytes_per_user", 100),
        max_uploads_per_user_per_hour=overrides.get(
            "max_uploads_per_user_per_hour", 20
        ),
        max_concurrent_uploads=overrides.get("max_concurrent_uploads", 4),
        max_concurrent_uploads_per_user=overrides.get(
            "max_concurrent_uploads_per_user", 2
        ),
        upload_lease_ttl_seconds=overrides.get("upload_lease_ttl_seconds", 60),
        max_image_dimension=overrides.get("max_image_dimension", 100),
        max_image_pixels=overrides.get("max_image_pixels", 10_000),
    )


def insert_user(active_settings: Settings, sub: str = "upload-user") -> int:
    with contextlib.closing(connect(active_settings)) as connection, connection:
        cursor = connection.execute(
            """
            INSERT INTO google_users (
                google_sub, email, name, picture, created_at, last_login_at
            ) VALUES (?, NULL, NULL, NULL, '2026-01-01', '2026-01-01')
            """,
            (sub,),
        )
        user_id = cursor.lastrowid
    assert user_id is not None
    return user_id


def insert_photo(
    active_settings: Settings,
    user_id: int,
    *,
    size_bytes: int,
    name: str = "existing",
) -> tuple[int, Path]:
    store = LocalPhotoStore(active_settings, name_factory=lambda: name)
    relative = store.save(user_id, ".png", b"x" * size_bytes)
    with contextlib.closing(connect(active_settings)) as connection, connection:
        cursor = connection.execute(
            """
            INSERT INTO memorial_photos (
                user_id, file_name, stored_path, content_type, taken_at,
                created_at, taken_at_utc, local_date, size_bytes
            ) VALUES (?, 'x.png', ?, 'image/png', '2026-07-14T10:00:00+09:00',
                      '2026-07-14T01:00:00Z', '2026-07-14T01:00:00Z',
                      '2026-07-14', ?)
            """,
            (user_id, relative.as_posix(), size_bytes),
        )
        photo_id = cursor.lastrowid
    assert photo_id is not None
    return photo_id, relative


def admission(
    active_settings: Settings,
    *,
    lease_id: str,
    free_bytes: int = 10_000,
    clock: Callable[[], dt.datetime] | None = None,
) -> UploadAdmission:
    return UploadAdmission(
        active_settings,
        store=LocalPhotoStore(active_settings),
        clock=clock or (lambda: NOW),
        disk_free_bytes=lambda _path: free_bytes,
        lease_id_factory=lambda: lease_id,
    )


def png(width: int = 4, height: int = 4) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "blue").save(buffer, "PNG")
    return buffer.getvalue()
