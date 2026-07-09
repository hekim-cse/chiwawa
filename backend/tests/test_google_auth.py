# Run from backend/ directory:
#   cd /Users/chaeyeon/Chiwawa/chiwawa/backend
#   python -m pytest -q tests/test_google_auth.py
# 서버 실행:
#   python -m uvicorn chiwawa_backend.main:app --reload --host 0.0.0.0 --port 8000
# 테스트 url: http://localhost:8000/api/v1/auth/google/login

from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app


@pytest.mark.anyio
async def test_google_login_redirects_to_google_authorize_url() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/auth/google/login",
            follow_redirects=False,
        )

        assert response.is_redirect
        assert response.status_code == HTTPStatus.FOUND
        location = response.headers["location"]
        assert "accounts.google.com/o/oauth2/v2/auth" in location
        assert "client_id=" in location
        assert "redirect_uri=" in location