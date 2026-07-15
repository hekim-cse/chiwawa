from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Final

import jwt
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from chiwawa_backend.config import get_settings
from chiwawa_backend.errors import AuthenticationError
from chiwawa_backend.schemas.auth import (
    AccessTokenClaims,
    CurrentUserRead,
    TokenIdentity,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from chiwawa_backend.config import Settings

security = HTTPBearer(auto_error=False)
AUTH_EXPIRED_MESSAGE: Final = "token expired"
INVALID_AUTH_MESSAGE: Final = "invalid token"
MISSING_AUTH_MESSAGE: Final = "missing token"


def create_access_token(
    subject: str,
    payload: Mapping[str, str | None] | None = None,
    settings: Settings | None = None,
) -> str:
    now = datetime.now(UTC)
    identity = TokenIdentity.model_validate(payload or {})
    token_payload: dict[str, str | datetime | None] = {
        "sub": subject,
        "email": identity.email,
        "name": identity.name,
        "iat": now,
        "exp": now + timedelta(hours=8),
    }
    return jwt.encode(
        token_payload,
        (settings or get_settings()).require_jwt_secret(),
        algorithm="HS256",
    )


def decode_access_token(
    token: str,
    settings: Settings | None = None,
) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            (settings or get_settings()).require_jwt_secret(),
            algorithms=["HS256"],
        )
        return AccessTokenClaims.model_validate(payload)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError(AUTH_EXPIRED_MESSAGE) from exc
    except (jwt.InvalidTokenError, ValidationError) as exc:
        raise AuthenticationError(INVALID_AUTH_MESSAGE) from exc


def get_current_user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    settings: Settings | None = None,
) -> CurrentUserRead:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError(MISSING_AUTH_MESSAGE)
    claims = decode_access_token(credentials.credentials, settings)
    return CurrentUserRead(sub=claims.sub, email=claims.email, name=claims.name)
