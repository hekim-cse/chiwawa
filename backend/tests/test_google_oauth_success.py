from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.auth import GoogleAuthResponse

if TYPE_CHECKING:
    from pathlib import Path


def _configure_google_oauth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "http://test/api/v1/auth/google/callback",
    )


def _google_token_response(
    url: str,
    *,
    data: dict[str, str],
    timeout: float,
) -> httpx.Response:
    _ = data, timeout
    return httpx.Response(
        status_code=HTTPStatus.OK,
        json={
            "access_token": "google-access-token",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "openid email profile",
            "refresh_token": "google-refresh-token",
            "future_token_metadata": "ignored",
        },
        request=httpx.Request("POST", url),
    )


def _google_profile_response(
    url: str,
    *,
    headers: dict[str, str],
    timeout: float,
) -> httpx.Response:
    _ = headers, timeout
    return httpx.Response(
        status_code=HTTPStatus.OK,
        json={
            "sub": "google-user-123",
            "email": "traveler@example.com",
            "name": "Prototype Traveler",
            "given_name": "Prototype",
            "family_name": "Traveler",
            "locale": "ko",
            "future_profile_claim": "ignored",
        },
        request=httpx.Request("GET", url),
    )


@pytest.mark.anyio
async def test_google_callback_persists_typed_user_and_returns_documented_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: a valid OAuth login state and deterministic Google responses.
    _configure_google_oauth(monkeypatch)
    monkeypatch.setenv("JWT_SECRET", "test-only-secret-at-least-32-characters")
    db_path = tmp_path / "google_auth.db"
    monkeypatch.setenv("GOOGLE_AUTH_DB_PATH", str(db_path))
    monkeypatch.setattr(httpx, "post", _google_token_response)
    monkeypatch.setattr(httpx, "get", _google_profile_response)
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        login_response = await client.get(
            "/api/v1/auth/google/login",
            follow_redirects=False,
        )
        state = parse_qs(urlparse(login_response.headers["location"]).query)["state"][0]

        # When: Google redirects back with the matching state and code.
        response = await client.get(
            f"/api/v1/auth/google/callback?code=test-code&state={state}",
        )
        client.cookies.set("chiwawa_oauth_state", state)
        replay_response = await client.get(
            f"/api/v1/auth/google/callback?code=test-code&state={state}",
        )

    # Then: the package schema initializes SQLite and the typed response includes JWT.
    assert response.status_code == HTTPStatus.OK
    auth = GoogleAuthResponse.model_validate_json(response.text)
    assert auth.user.google_sub == "google-user-123"
    assert auth.access_token
    assert db_path.is_file()
    assert db_path.stat().st_mode & 0o777 == 0o600
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert replay_response.status_code == HTTPStatus.BAD_REQUEST
