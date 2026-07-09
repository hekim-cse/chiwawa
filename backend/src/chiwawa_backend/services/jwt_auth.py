from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def _get_secret() -> str:
    secret = os.getenv("JWT_SECRET", "dev-secret-change-me-please-use-a-long-random-string")
    return secret


def create_access_token(subject: str, payload: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    token_payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(hours=8),
    }
    if payload:
        token_payload.update(payload)
    return jwt.encode(token_payload, _get_secret(), algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _get_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc


def get_current_user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
) -> dict[str, Any]:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    return decode_access_token(credentials.credentials)
