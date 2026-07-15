from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import compare_digest, token_urlsafe
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from chiwawa_backend.config import Settings
from chiwawa_backend.dependencies import get_app_settings, get_oauth_state_store
from chiwawa_backend.routers.responses import error_responses
from chiwawa_backend.schemas.auth import (
    CurrentUserRead,
    GoogleAuthResponse,
    GoogleTokenResponse,
    GoogleUserProfile,
)
from chiwawa_backend.services.auth import save_or_update_user
from chiwawa_backend.services.jwt_auth import (
    create_access_token,
    get_current_user_from_credentials,
    security,
)
from chiwawa_backend.services.oauth_state_store import (
    OAuthStateCapacityError,
    OAuthStateCollisionError,
    OAuthStateStore,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
OAuthStateDep = Annotated[OAuthStateStore, Depends(get_oauth_state_store)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
OAUTH_STATE_COOKIE = "chiwawa_oauth_state"
OAUTH_COOKIE_PATH = "/api/v1/auth/google"
MAX_OAUTH_STATE_ISSUE_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class OAuthCallbackParams:
    code: str
    state_value: str


def _oauth_callback_params(
    code: Annotated[str, Query(min_length=1, max_length=4096)],
    state_value: Annotated[
        str,
        Query(
            alias="state",
            min_length=40,
            max_length=128,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ],
    state_cookie: Annotated[
        str,
        Cookie(
            alias=OAUTH_STATE_COOKIE,
            min_length=40,
            max_length=128,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ],
) -> OAuthCallbackParams:
    if not compare_digest(
        state_value.encode(),
        state_cookie.encode(),
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid OAuth state",
        )
    return OAuthCallbackParams(code=code, state_value=state_value)


def _issue_oauth_state(
    oauth_states: OAuthStateStore,
    expires_at: datetime,
) -> str:
    for _attempt in range(MAX_OAUTH_STATE_ISSUE_ATTEMPTS):
        oauth_state = token_urlsafe(32)
        try:
            oauth_states.issue(oauth_state, expires_at)
        except OAuthStateCollisionError:
            continue
        return oauth_state
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="OAuth state generation unavailable",
    )


@router.get(
    "/google/login",
    status_code=status.HTTP_302_FOUND,
    response_class=RedirectResponse,
    responses=error_responses(429, 500, 503),
)
def google_login(
    settings: SettingsDep,
    oauth_states: OAuthStateDep,
) -> RedirectResponse:
    oauth = settings.require_google_oauth()
    expires_at = datetime.now(UTC) + timedelta(
        seconds=settings.google_oauth_state_ttl_seconds,
    )
    try:
        oauth_state = _issue_oauth_state(oauth_states, expires_at)
    except OAuthStateCapacityError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="OAuth login capacity reached",
        ) from exc
    params = {
        "client_id": oauth.client_id,
        "redirect_uri": oauth.redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": oauth_state,
    }
    authorize_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        params,
    )
    response = RedirectResponse(status_code=status.HTTP_302_FOUND, url=authorize_url)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=oauth_state,
        max_age=settings.google_oauth_state_ttl_seconds,
        secure=settings.google_oauth_cookie_secure,
        httponly=True,
        samesite="lax",
        path=OAUTH_COOKIE_PATH,
    )
    _set_no_store_headers(response)
    return response


@router.get(
    "/google/callback",
    response_model=GoogleAuthResponse,
    responses=error_responses(400, 422, 500, 502),
)
def google_callback(
    response: Response,
    oauth_states: OAuthStateDep,
    settings: SettingsDep,
    callback: Annotated[OAuthCallbackParams, Depends(_oauth_callback_params)],
) -> GoogleAuthResponse:
    if not oauth_states.consume(callback.state_value, datetime.now(UTC)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid OAuth state",
        )

    oauth = settings.require_google_oauth()
    token = _exchange_code(
        callback.code,
        oauth.client_id,
        oauth.client_secret,
        oauth.redirect_uri,
    )
    profile = _fetch_google_profile(token.access_token)
    user = save_or_update_user(profile, settings)
    access_token = create_access_token(
        subject=user.id,
        payload={"email": user.email, "name": user.name},
        settings=settings,
    )
    response.delete_cookie(key=OAUTH_STATE_COOKIE, path=OAUTH_COOKIE_PATH)
    _set_no_store_headers(response)
    return GoogleAuthResponse(user=user, access_token=access_token)


@router.get(
    "/me",
    response_model=CurrentUserRead,
    responses=error_responses(401, 500),
)
def get_me(
    settings: SettingsDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> CurrentUserRead:
    return get_current_user_from_credentials(credentials, settings)


def _exchange_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> GoogleTokenResponse:
    try:
        response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
        _ = response.raise_for_status()
        return GoogleTokenResponse.model_validate_json(response.text)
    except (httpx.HTTPError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google token exchange failed",
        ) from exc


def _fetch_google_profile(access_token: str) -> GoogleUserProfile:
    try:
        response = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        _ = response.raise_for_status()
        return GoogleUserProfile.model_validate_json(response.text)
    except (httpx.HTTPError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google profile request failed",
        ) from exc


def _set_no_store_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
