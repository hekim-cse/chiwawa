from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from chiwawa_backend.config import Settings
from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.auth import GoogleAuthResponse

if TYPE_CHECKING:
    from pathlib import Path


def _google_token_response(
    url: str,
    *,
    data: dict[str, str],
    timeout: float,
) -> httpx.Response:
    _ = data, timeout
    return httpx.Response(
        status_code=HTTPStatus.OK,
        json={"access_token": "provider-token"},
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
            "sub": "injected-user",
            "email": "injected@example.test",
            "name": "Injected User",
        },
        request=httpx.Request("GET", url),
    )


@pytest.mark.anyio
async def test_injected_settings_auth_handoff_works_without_jwt_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: two apps share injected settings while JWT_SECRET is absent from env.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setattr(httpx, "post", _google_token_response)
    monkeypatch.setattr(httpx, "get", _google_profile_response)
    settings = Settings(
        database_path=tmp_path / "auth.db",
        google_client_id="client",
        google_client_secret=SecretStr("provider-secret"),
        google_redirect_uri="http://test/api/v1/auth/google/callback",
        jwt_secret=SecretStr("injected-jwt-secret-at-least-32-characters"),
    )
    login_app = create_app(settings=settings)
    callback_app = create_app(settings=settings)

    async with AsyncClient(
        transport=ASGITransport(app=login_app), base_url="http://test"
    ) as login_client:
        login = await login_client.get(
            "/api/v1/auth/google/login",
            follow_redirects=False,
        )
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]

    # When: another app consumes state, mints its JWT, and authenticates `/me`.
    async with AsyncClient(
        transport=ASGITransport(app=callback_app), base_url="http://test"
    ) as callback_client:
        callback_client.cookies.set("chiwawa_oauth_state", state)
        callback = await callback_client.get(
            f"/api/v1/auth/google/callback?code=test-code&state={state}"
        )
        if callback.status_code == HTTPStatus.OK:
            auth = GoogleAuthResponse.model_validate_json(callback.text)
            me = await callback_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {auth.access_token}"},
            )
        else:
            me = callback

    # Then: every auth operation uses the same app-injected signing configuration.
    assert callback.status_code == HTTPStatus.OK
    assert me.status_code == HTTPStatus.OK
    assert me.json()["email"] == "injected@example.test"
