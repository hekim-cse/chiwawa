from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials

from chiwawa_backend.schemas.auth import GoogleAuthResponse, GoogleUserRead
from chiwawa_backend.services.auth import save_or_update_user
from chiwawa_backend.services.jwt_auth import (
    create_access_token,
    get_current_user_from_credentials,
    security,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/google/login")
def google_login(request: Request) -> RedirectResponse:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    scope = "openid email profile"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
    }
    authorize_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(status_code=302, url=authorize_url)


@router.get("/google/callback")
def google_callback(request: Request) -> JSONResponse:
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="authorization code is required")

    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    token_payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    token_response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data=token_payload,
        timeout=10.0,
    )
    token_response.raise_for_status()
    access_token = token_response.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="failed to obtain access token")

    user_response = httpx.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10.0,
    )
    user_response.raise_for_status()
    user_profile = user_response.json()

    stored_user = save_or_update_user(
        {
            "sub": user_profile.get("sub"),
            "email": user_profile.get("email"),
            "name": user_profile.get("name"),
            "picture": user_profile.get("picture"),
        }
    )
    user = GoogleUserRead.model_validate(
        {
            "id": str(stored_user["id"]),
            "google_sub": str(stored_user["google_sub"]),
            "email": stored_user.get("email"),
            "name": stored_user.get("name"),
            "picture": stored_user.get("picture"),
            "created_at": stored_user["created_at"],
            "last_login_at": stored_user["last_login_at"],
        }
    )
    response = GoogleAuthResponse(user=user)
    access_token = create_access_token(
        subject=str(user.id),
        payload={"email": user.email, "name": user.name},
    )
    payload = response.model_dump(mode="json")
    payload["access_token"] = access_token
    return JSONResponse(status_code=200, content=payload)


@router.get("/me")
def get_me(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> JSONResponse:
    user = get_current_user_from_credentials(credentials)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"sub": user.get("sub"), "email": user.get("email"), "name": user.get("name")},
    )
