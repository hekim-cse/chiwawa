from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import anyio
import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.config import DeploymentMode
from chiwawa_backend.main import create_app
from tests.memorial_test_support import settings

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.config import Settings

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


async def _readiness_status(active_settings: Settings) -> tuple[int, JsonValue]:
    app = create_app(settings=active_settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client,
    ):
        response = await client.get("/ready")
    return response.status_code, cast("JsonValue", response.json())


@pytest.mark.anyio
async def test_ready_reports_healthy_dependencies(tmp_path: Path) -> None:
    status_code, payload = await _readiness_status(settings(tmp_path))

    assert status_code == HTTPStatus.OK
    assert payload == {
        "status": "ready",
        "service": "chiwawa-backend",
        "version": "0.1.0",
    }


@pytest.mark.anyio
async def test_ready_rejects_database_directory(tmp_path: Path) -> None:
    active_settings = settings(tmp_path)
    active_settings.auth_db_path().mkdir()

    status_code, payload = await _readiness_status(active_settings)

    assert status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert payload == {"detail": "service dependencies unavailable"}


@pytest.mark.anyio
async def test_ready_recovers_after_database_path_becomes_available(
    tmp_path: Path,
) -> None:
    active_settings = settings(tmp_path)
    database_path = active_settings.auth_db_path()
    database_path.mkdir()
    app = create_app(settings=active_settings)

    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client,
    ):
        unavailable = await client.get("/ready")
        assert unavailable.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        database_path.rmdir()
        await anyio.sleep(1.1)
        assert (await client.get("/ready")).status_code == HTTPStatus.OK


@pytest.mark.anyio
async def test_ready_rejects_non_directory_photo_root(tmp_path: Path) -> None:
    active_settings = settings(tmp_path)
    _ = active_settings.photo_dir_path().write_bytes(b"not-a-directory")

    status_code, payload = await _readiness_status(active_settings)

    assert status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert payload == {"detail": "service dependencies unavailable"}


@pytest.mark.anyio
async def test_ready_recovers_after_photo_root_becomes_available(
    tmp_path: Path,
) -> None:
    active_settings = settings(tmp_path)
    photo_root = active_settings.photo_dir_path()
    _ = photo_root.write_bytes(b"not-a-directory")
    app = create_app(settings=active_settings)

    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client,
    ):
        unavailable = await client.get("/ready")
        assert unavailable.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        photo_root.unlink()
        await anyio.sleep(1.1)
        assert (await client.get("/ready")).status_code == HTTPStatus.OK


@pytest.mark.anyio
async def test_ready_enforces_disk_watermark(tmp_path: Path) -> None:
    active_settings = settings(tmp_path, min_free_disk_bytes=10**30)

    status_code, payload = await _readiness_status(active_settings)

    assert status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert payload == {"detail": "service dependencies unavailable"}


@pytest.mark.anyio
async def test_ready_reports_invalid_production_configuration(
    tmp_path: Path,
) -> None:
    active_settings = settings(tmp_path).model_copy(
        update={
            "app_env": DeploymentMode.PRODUCTION,
            "database_path": tmp_path / "app.db",
        },
    )

    status_code, payload = await _readiness_status(active_settings)

    assert status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert payload == {"detail": "service dependencies unavailable"}
