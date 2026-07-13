from __future__ import annotations

from datetime import UTC, datetime, timedelta
from secrets import compare_digest, token_urlsafe
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from chiwawa_backend.config import get_settings
from chiwawa_backend.dependencies import get_state
from chiwawa_backend.schemas.auth import (
    CurrentUserRead,
    GoogleAuthResponse,
    GoogleTokenResponse,
    GoogleUserProfile,
)
from chiwawa_backend.schemas.base import ErrorResponse
from chiwawa_backend.services.auth import save_or_update_user
from chiwawa_backend.services.jwt_auth import (
    create_access_token,
    get_current_user_from_credentials,
    security,
)
from chiwawa_backend.state import AppState

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
StateDep = Annotated[AppState, Depends(get_state)]
OAUTH_STATE_COOKIE = "chiwawa_oauth_state"
OAUTH_COOKIE_PATH = "/api/v1/auth/google"


@router.get(
    "/google/login",
    status_code=status.HTTP_302_FOUND,
    response_class=RedirectResponse,
)
def google_login(app_state: StateDep) -> RedirectResponse:
    settings = get_settings()
    oauth = settings.require_google_oauth()
    oauth_state = token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(
        seconds=settings.google_oauth_state_ttl_seconds,
    )
    app_state.issue_oauth_state(oauth_state, expires_at)
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
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
    },
)
def google_callback(
    response: Response,
    app_state: StateDep,
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
) -> GoogleAuthResponse:
    if not compare_digest(
        state_value.encode(),
        state_cookie.encode(),
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid OAuth state",
        )
    if not app_state.consume_oauth_state(state_value, datetime.now(UTC)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid OAuth state",
        )

    settings = get_settings()
    oauth = settings.require_google_oauth()
    token = _exchange_code(
        code,
        oauth.client_id,
        oauth.client_secret,
        oauth.redirect_uri,
    )
    profile = _fetch_google_profile(token.access_token)
    user = save_or_update_user(profile, settings)
    access_token = create_access_token(
        subject=user.id,
        payload={"email": user.email, "name": user.name},
    )
    response.delete_cookie(key=OAUTH_STATE_COOKIE, path=OAUTH_COOKIE_PATH)
    _set_no_store_headers(response)
    return GoogleAuthResponse(user=user, access_token=access_token)


@router.get(
    "/me",
    response_model=CurrentUserRead,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
def get_me(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> CurrentUserRead:
    return get_current_user_from_credentials(credentials)


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
