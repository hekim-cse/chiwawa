from __future__ import annotations

import contextlib
import sqlite3
from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from chiwawa_backend.errors import DomainValidationError, UnsupportedMediaTypeError
from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.auth import GoogleUserProfile
from chiwawa_backend.services import memorial_photos
from chiwawa_backend.services.auth import save_or_update_user
from chiwawa_backend.services.exif import InvalidImageError, inspect_image
from chiwawa_backend.services.jwt_auth import create_access_token
from chiwawa_backend.services.local_photo_store import LocalPhotoStore
from chiwawa_backend.services.memorial_photos import PhotoUpload, save_photo
from tests.memorial_test_support import (
    admission,
    insert_user,
    png,
    settings,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from chiwawa_backend.config import Settings
    from chiwawa_backend.services.memorial_photo_repository import NewPhotoRecord
    from chiwawa_backend.services.upload_admission import UploadLease


def test_image_inspection_rejects_bombs_dimensions_and_pixels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: Pillow's warning threshold and explicit application limits are small.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)

    # When/Then: warning, dimension, and pixel violations become InvalidImageError.
    with pytest.raises(InvalidImageError):
        _ = inspect_image(png(4, 3), max_dimension=10, max_pixels=100)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", None)
    with pytest.raises(InvalidImageError):
        _ = inspect_image(png(5, 2), max_dimension=4, max_pixels=100)
    with pytest.raises(InvalidImageError):
        _ = inspect_image(png(5, 5), max_dimension=10, max_pixels=24)


@pytest.mark.anyio
async def test_mime_spoof_uses_detected_type_private_headers_and_active_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: app settings differ from process env and a PNG is declared as JPEG.
    active_settings = settings(tmp_path)
    monkeypatch.setenv("GOOGLE_AUTH_DB_PATH", str(tmp_path / "wrong.db"))
    monkeypatch.setenv("MEMORIAL_PHOTO_DIR", str(tmp_path / "wrong-photos"))
    monkeypatch.setenv("JWT_SECRET", "wrong-secret-at-least-32-characters-long")
    user = save_or_update_user(
        GoogleUserProfile(sub="mime-user", email=None, name=None),
        settings=active_settings,
    )
    token = create_access_token(subject=user.id, settings=active_settings)
    app = create_app(settings=active_settings)

    # When: the authenticated member uploads and downloads the spoofed file.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        uploaded = await client.post(
            "/api/v1/memorial/photos",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("spoof.jpg", png(), "image/jpeg")},
        )
        payload = cast("dict[str, object]", uploaded.json())
        metadata = await client.get(
            f"/api/v1/memorial/photos/{payload['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        calendar = await client.get(
            "/api/v1/memorial/calendar?year=2026&month=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        downloaded = await client.get(
            cast("str", payload["file_url"]),
            headers={"Authorization": f"Bearer {token}"},
        )

    # Then: detected MIME wins, local app paths are used, and responses are private.
    assert uploaded.status_code == HTTPStatus.CREATED
    assert payload["content_type"] == "image/png"
    assert uploaded.headers["cache-control"] == "private, no-store"
    assert uploaded.headers["x-content-type-options"] == "nosniff"
    assert downloaded.headers["content-type"] == "image/png"
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert metadata.headers["cache-control"] == "private, no-store"
    assert calendar.headers["cache-control"] == "private, no-store"
    assert downloaded.content == png()
    stored_files = list(
        active_settings.photo_dir_path().joinpath(str(user.id)).iterdir()
    )
    assert len(stored_files) == 1
    assert stored_files[0].suffix == ".png"
    assert not (tmp_path / "wrong.db").exists()
    assert not (tmp_path / "wrong-photos").exists()


def test_failed_validation_releases_lease_without_orphaned_file(tmp_path: Path) -> None:
    # Given: an authenticated user submits invalid image bytes after admission.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    store = LocalPhotoStore(active_settings)
    gate = admission(active_settings, lease_id="invalid")
    upload = PhotoUpload(
        file_name="invalid.jpg",
        content_type="image/jpeg",
        data=b"not-an-image",
        taken_at=None,
        latitude=None,
        longitude=None,
        memo=None,
    )

    # When: slow-path validation rejects the admitted upload.
    with pytest.raises(UnsupportedMediaTypeError):
        _ = save_photo(
            user_id,
            upload,
            settings=active_settings,
            store=store,
            admission=gate,
        )

    # Then: the lease is released, the rate attempt remains, and no file is orphaned.
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        leases = cast(
            "tuple[int] | None",
            connection.execute("SELECT COUNT(*) FROM upload_leases").fetchone(),
        )
        events = cast(
            "tuple[int] | None",
            connection.execute("SELECT COUNT(*) FROM upload_events").fetchone(),
        )
    assert leases == (0,)
    assert events == (1,)
    assert not any(path.is_file() for path in store.root.rglob("*"))


@pytest.mark.parametrize(
    ("file_name", "memo"),
    [("x" * 256, None), ("valid.png", "m" * 2001)],
)
def test_upload_metadata_lengths_are_bounded_before_admission(
    file_name: str,
    memo: str | None,
    tmp_path: Path,
) -> None:
    # Given: image metadata would otherwise consume an unbounded SQLite text field.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    store = LocalPhotoStore(active_settings)
    gate = admission(active_settings, lease_id="metadata-limit")
    upload = PhotoUpload(
        file_name=file_name,
        content_type="image/png",
        data=png(),
        taken_at=None,
        latitude=None,
        longitude=None,
        memo=memo,
    )

    # When/Then: the service rejects it before recording an upload attempt.
    with pytest.raises(DomainValidationError):
        _ = save_photo(
            user_id,
            upload,
            settings=active_settings,
            store=store,
            admission=gate,
        )
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path()),
    ) as connection:
        attempts = cast(
            "tuple[int] | None",
            connection.execute("SELECT COUNT(*) FROM upload_events").fetchone(),
        )
    assert attempts == (0,)


def test_database_insert_failure_removes_new_file_and_releases_lease(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: storage succeeds but the following metadata insert fails.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    store = LocalPhotoStore(active_settings, name_factory=lambda: "orphan")
    gate = admission(active_settings, lease_id="db-failure")

    def fail_insert(
        _settings: Settings,
        _photo: NewPhotoRecord,
        _lease: UploadLease,
        _active_at: Callable[[], str],
    ) -> int:
        message = "insert failed"
        raise sqlite3.OperationalError(message)

    monkeypatch.setattr(memorial_photos, "_insert_photo_row", fail_insert)
    upload = PhotoUpload(
        file_name="valid.png",
        content_type="image/png",
        data=png(),
        taken_at=None,
        latitude=None,
        longitude=None,
        memo=None,
    )

    # When: the service crosses the storage/database boundary.
    with pytest.raises(sqlite3.OperationalError):
        _ = memorial_photos.save_photo(
            user_id,
            upload,
            settings=active_settings,
            store=store,
            admission=gate,
        )

    # Then: compensation removes the file and reservation.
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        leases = cast(
            "tuple[int] | None",
            connection.execute("SELECT COUNT(*) FROM upload_leases").fetchone(),
        )
    assert leases == (0,)
    assert not any(path.is_file() for path in store.root.rglob("*"))


def test_release_failure_after_commit_does_not_replace_upload_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: metadata commits successfully but best-effort lease cleanup loses its DB.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    store = LocalPhotoStore(active_settings, name_factory=lambda: "committed")
    gate = admission(active_settings, lease_id="release-failure")

    def fail_release(_lease: UploadLease) -> None:
        message = "release unavailable"
        raise sqlite3.OperationalError(message)

    monkeypatch.setattr(gate, "release", fail_release)
    upload = PhotoUpload(
        file_name="valid.png",
        content_type="application/octet-stream",
        data=png(),
        taken_at=None,
        latitude=None,
        longitude=None,
        memo=None,
    )

    # When: the service returns the already committed photo.
    result = memorial_photos.save_photo(
        user_id,
        upload,
        settings=active_settings,
        store=store,
        admission=gate,
    )

    # Then: detected image content succeeds exactly once despite cleanup failure.
    assert result.content_type == "image/png"
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path()),
    ) as connection:
        photos = cast(
            "tuple[int] | None",
            connection.execute("SELECT COUNT(*) FROM memorial_photos").fetchone(),
        )
    assert photos == (1,)


def test_geocoding_failure_releases_lease_before_any_file_is_created(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: image validation succeeds but reverse geocoding raises unexpectedly.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    store = LocalPhotoStore(active_settings, name_factory=lambda: "geocode")
    gate = admission(active_settings, lease_id="geocode")

    def fail_geocode(_latitude: float, _longitude: float) -> str | None:
        message = "geocoder failed"
        raise RuntimeError(message)

    monkeypatch.setattr(memorial_photos, "reverse_geocode", fail_geocode)
    upload = PhotoUpload(
        file_name="valid.png",
        content_type="image/png",
        data=png(),
        taken_at=None,
        latitude=35.0,
        longitude=135.0,
        memo=None,
    )

    # When: the admitted service resolves location metadata.
    with pytest.raises(RuntimeError, match="geocoder failed"):
        _ = memorial_photos.save_photo(
            user_id,
            upload,
            settings=active_settings,
            store=store,
            admission=gate,
        )

    # Then: no file or active lease remains.
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        leases = cast(
            "tuple[int] | None",
            connection.execute("SELECT COUNT(*) FROM upload_leases").fetchone(),
        )
    assert leases == (0,)
    assert not any(path.is_file() for path in store.root.rglob("*"))


@pytest.mark.anyio
async def test_numeric_token_for_unknown_user_is_rejected_as_401(
    tmp_path: Path,
) -> None:
    # Given: a validly signed numeric JWT subject has no google_users row.
    active_settings = settings(tmp_path)
    token = create_access_token(subject="999", settings=active_settings)
    app = create_app(settings=active_settings)

    # When: that principal attempts an otherwise valid photo upload.
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/memorial/photos",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("valid.png", png(), "image/png")},
        )

    # Then: the established unknown-user contract is preserved.
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {"detail": "unknown user"}
