from __future__ import annotations

from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app


def _configure_google_oauth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "http://test/api/v1/auth/google/callback",
    )


def _unexpected_token_exchange(*args: object, **kwargs: object) -> None:
    _ = args, kwargs
    msg = "OAuth callback must reject invalid state before contacting Google"
    raise AssertionError(msg)


@pytest.mark.anyio
async def test_google_login_binds_redirect_to_http_only_state_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a configured local Google OAuth prototype.
    _configure_google_oauth(monkeypatch)
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: a browser begins Google login.
        response = await client.get(
            "/api/v1/auth/google/login",
            follow_redirects=False,
        )

    # Then: the redirect and an HttpOnly cookie share an unpredictable state value.
    assert response.status_code == HTTPStatus.FOUND
    query = parse_qs(urlparse(response.headers["location"]).query)
    state = query["state"][0]
    assert len(state) >= 40
    assert "access_type" not in query
    assert "prompt" not in query
    set_cookie = response.headers["set-cookie"].lower()
    assert f"chiwawa_oauth_state={state}".lower() in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.anyio
async def test_google_callback_requires_state_before_token_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a callback carrying a code but no state parameter.
    _configure_google_oauth(monkeypatch)
    monkeypatch.setattr(httpx, "post", _unexpected_token_exchange)
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        client.cookies.set("chiwawa_oauth_state", "x" * 43)

        # When: the unbound callback reaches the backend.
        response = await client.get("/api/v1/auth/google/callback?code=test-code")

    # Then: it is rejected locally without exchanging the authorization code.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_google_callback_rejects_mismatched_state_before_token_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a callback whose state differs from the login cookie.
    _configure_google_oauth(monkeypatch)
    monkeypatch.setattr(httpx, "post", _unexpected_token_exchange)
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        client.cookies.set("chiwawa_oauth_state", "x" * 43)

        # When: the callback attempts to use a different state value.
        response = await client.get(
            f"/api/v1/auth/google/callback?code=test-code&state={'y' * 43}",
        )

    # Then: it is rejected before any Google network call.
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["detail"] == "invalid OAuth state"


@pytest.mark.anyio
async def test_google_callback_rejects_non_ascii_state_without_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: an OAuth callback with a non-URL-safe state value.
    _configure_google_oauth(monkeypatch)
    monkeypatch.setattr(httpx, "post", _unexpected_token_exchange)
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        client.cookies.set("chiwawa_oauth_state", "expected-state")

        # When: the malformed state reaches request validation.
        response = await client.get(
            "/api/v1/auth/google/callback?code=test-code&state=%C3%A9",
        )

    # Then: it is rejected as input instead of escaping compare_digest as TypeError.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_google_callback_requires_browser_state_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a valid server-issued state obtained by a separate browser client.
    _configure_google_oauth(monkeypatch)
    monkeypatch.setattr(httpx, "post", _unexpected_token_exchange)
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as browser_client:
        login_response = await browser_client.get(
            "/api/v1/auth/google/login",
            follow_redirects=False,
        )
        state = parse_qs(urlparse(login_response.headers["location"]).query)["state"][0]

    # When: another HTTP client forwards state without the browser cookie.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as app_client:
        response = await app_client.get(
            f"/api/v1/auth/google/callback?code=test-code&state={state}",
        )

    # Then: the callback is rejected before any provider request.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
