from __future__ import annotations

import contextlib
import sqlite3
from http import HTTPStatus
from typing import TYPE_CHECKING, Final, final

from anyio import CancelScope
from anyio.to_thread import run_sync
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from starlette.responses import JSONResponse

from chiwawa_backend.dependencies import get_current_user_id
from chiwawa_backend.errors import (
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
)
from chiwawa_backend.middleware.headers import normalized_headers
from chiwawa_backend.services.upload_request_admission import (
    UploadRequestAdmission,
)

if TYPE_CHECKING:
    from starlette.datastructures import Headers
    from starlette.types import ASGIApp, Receive, Scope, Send

    from chiwawa_backend.config import Settings

UPLOAD_PATHS: Final = frozenset(
    {"/api/v1/memorial/photos", "/api/v1/memorial/photos/"},
)


@final
class EarlyUploadAuthMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self._app = app
        self._settings = settings
        self._request_admission = UploadRequestAdmission(settings)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not _is_protected_upload(scope):
            await self._app(scope, receive, send)
            return

        credentials = _bearer_credentials(normalized_headers(scope))
        try:
            user_id = get_current_user_id(self._settings, credentials)
        except AuthenticationError as error:
            await _error_response(error)(scope, receive, send)
            return
        try:
            slot = await run_sync(self._request_admission.acquire, user_id)
        except (AuthenticationError, RateLimitError) as error:
            await _error_response(error)(scope, receive, send)
            return
        except (ConfigurationError, OSError, sqlite3.Error):
            response = JSONResponse(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                content={"detail": "service dependencies unavailable"},
            )
            await response(scope, receive, send)
            return
        try:
            with self._request_admission.heartbeat(slot):
                await self._app(scope, receive, send)
        finally:
            with (
                CancelScope(shield=True),
                contextlib.suppress(ConfigurationError, OSError, sqlite3.Error),
            ):
                await run_sync(self._request_admission.release, slot)


def _is_protected_upload(scope: Scope) -> bool:
    return (
        scope["type"] == "http"
        and scope["method"] == "POST"
        and scope["path"] in UPLOAD_PATHS
    )


def _bearer_credentials(headers: Headers) -> HTTPAuthorizationCredentials | None:
    scheme, value = get_authorization_scheme_param(headers.get("authorization"))
    if scheme.lower() != "bearer" or not value:
        return None
    return HTTPAuthorizationCredentials(scheme=scheme, credentials=value)


def _error_response(error: AuthenticationError | RateLimitError) -> JSONResponse:
    status_code = (
        HTTPStatus.UNAUTHORIZED
        if isinstance(error, AuthenticationError)
        else HTTPStatus.TOO_MANY_REQUESTS
    )
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(error)},
        headers=error.headers,
    )
