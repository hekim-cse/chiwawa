from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from chiwawa_backend.services.jwt_auth import (
    get_current_user_from_credentials,
    security,
)
from chiwawa_backend.state import AppState


def get_state() -> AppState:
    message = "state dependency is not configured"
    raise RuntimeError(message)


def get_current_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> int:
    claims = get_current_user_from_credentials(credentials)
    subject: object = claims.get("sub")
    if not isinstance(subject, str) or not subject.isdigit():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token subject",
        )
    return int(subject)
