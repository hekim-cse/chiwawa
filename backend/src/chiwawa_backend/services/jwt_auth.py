from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from chiwawa_backend.config import get_settings
from chiwawa_backend.schemas.auth import (
    AccessTokenClaims,
    CurrentUserRead,
    TokenIdentity,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

security = HTTPBearer(auto_error=False)


def create_access_token(
    subject: str,
    payload: Mapping[str, str | None] | None = None,
) -> str:
    now = datetime.now(UTC)
    identity = TokenIdentity.model_validate(payload or {})
    token_payload: dict[str, object] = {
        "sub": subject,
        "email": identity.email,
        "name": identity.name,
        "iat": now,
        "exp": now + timedelta(hours=8),
    }
    return jwt.encode(
        token_payload,
        get_settings().require_jwt_secret(),
        algorithm="HS256",
    )


def decode_access_token(token: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            get_settings().require_jwt_secret(),
            algorithms=["HS256"],
        )
        return AccessTokenClaims.model_validate(payload)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token expired",
        ) from exc
    except (jwt.InvalidTokenError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        ) from exc


def get_current_user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
) -> CurrentUserRead:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing token",
        )
    claims = decode_access_token(credentials.credentials)
    return CurrentUserRead(sub=claims.sub, email=claims.email, name=claims.name)
