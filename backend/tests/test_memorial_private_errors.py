from __future__ import annotations

import sqlite3
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.services import memorial_photos
from chiwawa_backend.services.jwt_auth import create_access_token
from tests.memorial_test_support import insert_user, settings

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.config import Settings
    from chiwawa_backend.schemas.memorial import MemorialCalendarResponse


@pytest.mark.anyio
async def test_album_authentication_error_is_private(tmp_path: Path) -> None:
    # Given: an anonymous request targets private album metadata.
    app = create_app(settings=settings(tmp_path))

    # When: authentication rejects the request.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/memorial/photos/999")

    # Then: the terminal 401 cannot be stored by shared caches.
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/memorial/photos/999",
        "/api/v1/memorial/photos/999/file",
    ],
)
async def test_missing_album_resource_error_is_private(
    tmp_path: Path,
    path: str,
) -> None:
    # Given: an authenticated member requests missing private metadata or bytes.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    token = create_access_token(str(user_id), settings=active_settings)
    app = create_app(settings=active_settings)

    # When: ownership-scoped lookup returns not found.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            path,
            headers={"Authorization": f"Bearer {token}"},
        )

    # Then: the terminal 404 cannot be stored by shared caches.
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.anyio
async def test_invalid_album_image_error_is_private(tmp_path: Path) -> None:
    # Given: an authenticated member submits invalid image bytes.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    token = create_access_token(str(user_id), settings=active_settings)
    app = create_app(settings=active_settings)

    # When: image inspection rejects the admitted upload.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/memorial/photos",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("invalid.jpg", b"invalid", "image/jpeg")},
        )

    # Then: the terminal 415 cannot be stored by shared caches.
    assert response.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.anyio
async def test_unexpected_album_database_error_is_private(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    token = create_access_token(str(user_id), settings=active_settings)
    app = create_app(settings=active_settings)

    def unavailable_database(
        user_id: int,
        year: int,
        month: int,
        *,
        settings: Settings | None = None,
    ) -> MemorialCalendarResponse:
        _ = user_id, year, month, settings
        message = "database unavailable"
        raise sqlite3.OperationalError(message)

    monkeypatch.setattr(memorial_photos, "month_calendar", unavailable_database)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/memorial/calendar",
            params={"year": 2026, "month": 7},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Request-ID": "private-error",
            },
        )

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "internal server error"}
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-request-id"] == "private-error"
    assert response.headers["x-content-type-options"] == "nosniff"
