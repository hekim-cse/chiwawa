from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from secrets import compare_digest, token_urlsafe
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
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
def google_login(
    app_state: StateDep,
    popup_origin: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    settings = get_settings()
    oauth = settings.require_google_oauth()
    oauth_state = token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(
        seconds=settings.google_oauth_state_ttl_seconds,
    )
    if popup_origin is not None and popup_origin not in settings.allowed_origins():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="허용되지 않은 OAuth 팝업 출처입니다.",
        )
    app_state.issue_oauth_state(oauth_state, expires_at, popup_origin)
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
def google_callback(  # noqa: PLR0913 - FastAPI 계약별 요청 요소를 명시적으로 주입
    request: Request,
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
) -> GoogleAuthResponse | HTMLResponse:
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
    popup_origin = app_state.consume_oauth_popup_origin(state_value)

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
    auth = GoogleAuthResponse(user=user, access_token=access_token)
    if popup_origin is not None:
        popup_response = _oauth_popup_response(auth, popup_origin)
        popup_response.delete_cookie(key=OAUTH_STATE_COOKIE, path=OAUTH_COOKIE_PATH)
        _set_no_store_headers(popup_response)
        return popup_response
    if "text/html" in request.headers.get("accept", ""):
        browser_response = _oauth_browser_without_popup_response()
        browser_response.delete_cookie(
            key=OAUTH_STATE_COOKIE,
            path=OAUTH_COOKIE_PATH,
        )
        _set_no_store_headers(browser_response)
        return browser_response
    response.delete_cookie(key=OAUTH_STATE_COOKIE, path=OAUTH_COOKIE_PATH)
    _set_no_store_headers(response)
    return auth


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


def _oauth_popup_response(
    auth: GoogleAuthResponse,
    popup_origin: str,
) -> HTMLResponse:
    message = json.dumps(
        {
            "type": "chiwawa-google-oauth-success",
            "payload": auth.model_dump(mode="json"),
        },
        ensure_ascii=False,
    )
    message_literal = json.dumps(message).replace("<", "\\u003c")
    target_origin = json.dumps(popup_origin)
    html = f"""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><title>로그인 완료</title></head>
<body>
<p>로그인이 완료되었습니다. 앱으로 돌아가는 중입니다.</p>
<script>
window.opener?.postMessage({message_literal}, {target_origin});
</script>
</body>
</html>"""
    return HTMLResponse(
        content=html,
        headers={
            "Content-Security-Policy": (
                "default-src 'none'; script-src 'unsafe-inline'; "
                "style-src 'none'; frame-ancestors 'none'"
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )


def _oauth_browser_without_popup_response() -> HTMLResponse:
    return HTMLResponse(
        content="""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><title>로그인 다시 시작</title></head>
<body>
<p>앱의 Google 로그인 버튼에서 다시 시작해 주세요.</p>
</body>
</html>""",
        headers={
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
        },
    )
