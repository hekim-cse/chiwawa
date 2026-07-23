# 메모리얼 데모 모드 테스트 (로그인 없이 앨범 조회)
#   cd backend && uv run pytest tests/test_memorial_demo_mode.py

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def demo_db_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GOOGLE_AUTH_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MEMORIAL_PHOTO_DIR", str(tmp_path / "photos"))
    monkeypatch.setenv("JWT_SECRET", "test-only-secret-at-least-32-characters")


@pytest.mark.anyio
@pytest.mark.usefixtures("demo_db_env")
async def test_demo_mode_lets_guest_read_memorial_calendar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: 데모 모드가 켜져 있다.
    monkeypatch.setenv("MEMORIAL_DEMO_MODE", "true")
    app = create_app()

    # When: 토큰 없이(게스트) 캘린더를 조회한다.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/memorial/calendar",
            params={"year": 2026, "month": 7},
        )

    # Then: 401이 아니라 데모 유저의 (빈) 캘린더가 200으로 온다.
    assert response.status_code == HTTPStatus.OK


@pytest.mark.anyio
@pytest.mark.usefixtures("demo_db_env")
async def test_without_demo_mode_guest_is_unauthorized() -> None:
    # Given: 데모 모드가 꺼져 있다(기본값).
    app = create_app()

    # When: 토큰 없이 캘린더를 조회한다.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/memorial/calendar",
            params={"year": 2026, "month": 7},
        )

    # Then: 기존대로 401로 막힌다.
    assert response.status_code == HTTPStatus.UNAUTHORIZED
