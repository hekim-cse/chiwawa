from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.services.jwt_auth import create_access_token


@pytest.mark.anyio
async def test_me_endpoint_requires_valid_jwt() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        token = create_access_token(
            "user-123",
            {"email": "test@example.com", "name": "Test User"},
        )
        authorized_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert authorized_response.status_code == HTTPStatus.OK
        assert authorized_response.json()["sub"] == "user-123"
