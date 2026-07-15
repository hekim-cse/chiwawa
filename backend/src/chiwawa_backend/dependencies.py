from typing import Annotated, Final

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from chiwawa_backend.config import Settings, get_settings
from chiwawa_backend.errors import AuthenticationError
from chiwawa_backend.schemas.trips import TripRead
from chiwawa_backend.services.common import (
    require_trip_access as require_trip_access_for_actor,
)
from chiwawa_backend.services.jwt_auth import (
    get_current_user_from_credentials,
    security,
)
from chiwawa_backend.services.oauth_state_store import OAuthStateStore
from chiwawa_backend.services.readiness import StartupRecoveryStatus
from chiwawa_backend.state import AppState

MAX_SQLITE_INTEGER: Final = (1 << 63) - 1
INVALID_SUBJECT_DETAIL: Final = "invalid token subject"


def get_transaction_state() -> AppState:
    message = "state dependency is not configured"
    raise RuntimeError(message)


def get_state(
    state: Annotated[
        AppState,
        Depends(get_transaction_state, scope="function"),
    ],
) -> AppState:
    return state


def get_oauth_state_store() -> OAuthStateStore:
    message = "OAuth state store dependency is not configured"
    raise RuntimeError(message)


def get_app_settings() -> Settings:
    return get_settings()


def get_startup_recovery_status() -> StartupRecoveryStatus:
    message = "startup recovery dependency is not configured"
    raise RuntimeError(message)


StateDep = Annotated[AppState, Depends(get_state)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
StartupRecoveryDep = Annotated[
    StartupRecoveryStatus,
    Depends(get_startup_recovery_status),
]
CredentialsDep = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(security),
]


def get_current_user_id(
    settings: SettingsDep,
    credentials: CredentialsDep,
) -> int:
    claims = get_current_user_from_credentials(credentials, settings)
    subject = claims.sub
    if not subject.isascii() or not subject.isdecimal():
        raise _invalid_token_subject()
    try:
        user_id = int(subject)
    except ValueError as error:
        raise _invalid_token_subject() from error
    if not 0 < user_id <= MAX_SQLITE_INTEGER:
        raise _invalid_token_subject()
    return user_id


def _invalid_token_subject() -> AuthenticationError:
    return AuthenticationError(INVALID_SUBJECT_DETAIL)


def get_actor_id(settings: SettingsDep, credentials: CredentialsDep) -> int:
    if not settings.is_production:
        return 0
    return get_current_user_id(settings, credentials)


ActorIdDep = Annotated[int, Depends(get_actor_id)]


def require_trip_access(
    trip_id: str,
    actor_id: ActorIdDep,
    settings: SettingsDep,
    state: StateDep,
) -> TripRead:
    return require_trip_access_for_actor(
        state,
        trip_id,
        actor_id,
        allow_unowned=not settings.is_production,
    )


TripAccessDep = Annotated[TripRead, Depends(require_trip_access)]
