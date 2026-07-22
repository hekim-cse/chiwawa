# CORS 미들웨어 테스트
#   cd backend && uv run pytest tests/test_cors.py

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app

ALLOWED_ORIGIN = "http://localhost:8080"
DISALLOWED_ORIGIN = "http://evil.example"


@pytest.mark.anyio
async def test_preflight_from_allowed_origin_is_permitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: 설정에 등록된 프론트 오리진.
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", ALLOWED_ORIGIN)
    app = create_app()

    # When: 브라우저가 실제 요청 전 preflight(OPTIONS)를 보낸다.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )

    # Then: 해당 오리진을 그대로 반사하고 자격 증명 사용을 허용한다.
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.anyio
async def test_disallowed_origin_gets_no_cors_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: 등록되지 않은 오리진에서의 요청.
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", ALLOWED_ORIGIN)
    app = create_app()

    # When: 다른 오리진으로 실제 요청을 보낸다.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/health",
            headers={"Origin": DISALLOWED_ORIGIN},
        )

    # Then: 허용 오리진 헤더가 붙지 않아 브라우저가 응답을 차단한다.
    assert "access-control-allow-origin" not in response.headers
