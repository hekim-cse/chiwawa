from __future__ import annotations

import os
from http import HTTPStatus
from typing import TYPE_CHECKING

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.services.jwt_auth import create_access_token

if TYPE_CHECKING:
    from pathlib import Path


def test_access_token_requires_explicit_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: no JWT signing secret in the process environment.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    # When / Then: the backend refuses to mint a token with a public fallback key.
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _ = create_access_token("user-123")


@pytest.mark.anyio
async def test_me_endpoint_requires_valid_jwt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: an explicit development-only signing secret.
    monkeypatch.setenv("JWT_SECRET", "test-only-secret-at-least-32-characters")
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: the endpoint receives no token and then a valid token.
        response = await client.get("/api/v1/auth/me")
        token = create_access_token(
            "user-123",
            {"email": "test@example.com", "name": "Test User"},
        )
        authorized_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    # Then: only the signed request exposes the typed user claims.
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert authorized_response.status_code == HTTPStatus.OK
    assert authorized_response.json()["sub"] == "user-123"


@pytest.mark.anyio
async def test_me_rejects_signed_token_missing_required_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a correctly signed token that does not contain identity claims.
    monkeypatch.setenv("JWT_SECRET", "test-only-secret-at-least-32-characters")
    malformed_token = jwt.encode({}, os.environ["JWT_SECRET"], algorithm="HS256")
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: the malformed token is used on the protected endpoint.
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {malformed_token}"},
        )

    # Then: invalid claims are treated as authentication failure, not a server error.
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["detail"] == "invalid token"
