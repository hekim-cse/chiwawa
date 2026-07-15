from __future__ import annotations

import re
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Final, Literal, NotRequired, TypedDict, final
from uuid import uuid4

from pydantic import TypeAdapter
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse

from chiwawa_backend.middleware.headers import normalized_headers

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

MEMORIAL_ALBUM_PREFIX: Final = "/api/v1/memorial"
PRIVATE_CACHE_CONTROL: Final = "private, no-store"
SAFE_REQUEST_ID: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
REQUEST_TOO_LARGE_DETAIL: Final = "request body is too large"
INVALID_CONTENT_LENGTH_DETAIL: Final = "invalid content-length"
AMBIGUOUS_FRAMING_DETAIL: Final = "ambiguous request framing"
HTTP_ONE_VERSIONS: Final = frozenset({"1.0", "1.1"})
SECURITY_HEADERS: Final = (
    ("x-content-type-options", "nosniff"),
    ("x-frame-options", "DENY"),
    ("referrer-policy", "no-referrer"),
    (
        "content-security-policy",
        "frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
    ),
    ("permissions-policy", "camera=(), microphone=(), geolocation=()"),
)


class _HTTPRequestMessage(TypedDict):
    type: Literal["http.request"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


HTTP_REQUEST_MESSAGE_ADAPTER: Final = TypeAdapter(_HTTPRequestMessage)


class _HTTPResponseBodyMessage(TypedDict):
    type: Literal["http.response.body"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


HTTP_RESPONSE_BODY_ADAPTER: Final = TypeAdapter(_HTTPResponseBodyMessage)
HTTP_VERSION_ADAPTER: Final = TypeAdapter(str)
PATH_ADAPTER: Final = TypeAdapter(str)


class _InvalidContentLengthError(ValueError):
    pass


class _RequestBodyTooLargeError(Exception):
    pass


@final
class RequestBodyLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        max_json_body_bytes: int,
        max_multipart_body_bytes: int,
    ) -> None:
        self._app = app
        self._json_limit = max_json_body_bytes
        self._multipart_limit = max_multipart_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = normalized_headers(scope)
        limit = _request_limit(headers, self._json_limit, self._multipart_limit)
        http_version = HTTP_VERSION_ADAPTER.validate_python(
            scope["http_version"],
            strict=True,
        )
        if response := _declared_length_error(headers, limit, http_version):
            await response(scope, receive, send)
            return

        guard = _BodyReceiveGuard(scope, receive, send, limit)
        try:
            await self._app(scope, guard.receive_limited, guard.send_guarded)
        except _RequestBodyTooLargeError:
            return


@final
class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        response_security_headers = hardened_response_headers(
            normalized_headers(scope),
            PATH_ADAPTER.validate_python(scope["path"], strict=True),
        )

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                for name, value in response_security_headers.items():
                    if name == "cache-control":
                        _ = response_headers.setdefault(name, value)
                    else:
                        response_headers[name] = value
            await send(message)

        await self._app(scope, receive, send_with_headers)


@dataclass(slots=True)  # noqa: RUF100  # noqa: MUTABLE_OK
class _BodyReceiveGuard:
    """Close an overflowed started response once, then suppress downstream sends."""

    scope: Scope
    receive: Receive
    send: Send
    limit: int
    consumed: int = 0
    downstream_started: bool = False
    response_completed: bool = False
    limit_exceeded: bool = False

    async def receive_limited(self) -> Message:
        message = await self.receive()
        if message["type"] != "http.request":
            return message
        request_message = HTTP_REQUEST_MESSAGE_ADAPTER.validate_python(
            message,
            strict=True,
        )
        self.consumed += len(request_message.get("body", b""))
        if self.consumed <= self.limit:
            return message
        self.limit_exceeded = True
        if not self.downstream_started:
            self.response_completed = True
            await _too_large_response()(self.scope, self.receive, self.send)
        elif not self.response_completed:
            self.response_completed = True
            await self.send(
                {"type": "http.response.body", "body": b"", "more_body": False},
            )
        raise _RequestBodyTooLargeError

    async def send_guarded(self, message: Message) -> None:
        if self.limit_exceeded:
            return
        if message["type"] == "http.response.start":
            self.downstream_started = True
        await self.send(message)
        if message["type"] == "http.response.body":
            response_body = HTTP_RESPONSE_BODY_ADAPTER.validate_python(
                message,
                strict=True,
            )
            if not response_body.get("more_body", False):
                self.response_completed = True


def hardened_response_headers(
    request_headers: Headers,
    path: str,
) -> dict[str, str]:
    headers = {
        "x-request-id": _request_id(request_headers),
        **dict(SECURITY_HEADERS),
    }
    if path == MEMORIAL_ALBUM_PREFIX or path.startswith(f"{MEMORIAL_ALBUM_PREFIX}/"):
        headers["cache-control"] = PRIVATE_CACHE_CONTROL
    return headers


def _request_limit(headers: Headers, json_limit: int, multipart_limit: int) -> int:
    content_type = headers.get("content-type", "")
    media_type = content_type.partition(";")[0].strip().lower()
    return multipart_limit if media_type.startswith("multipart/") else json_limit


def _declared_content_length(headers: Headers) -> int | None:
    raw_values = headers.getlist("content-length")
    if not raw_values:
        return None
    tokens = [token.strip() for raw in raw_values for token in raw.split(",")]
    if not tokens or any(
        not token or not token.isascii() or not token.isdecimal() for token in tokens
    ):
        raise _InvalidContentLengthError
    try:
        lengths = {int(token) for token in tokens}
    except ValueError as error:
        raise _InvalidContentLengthError from error
    if len(lengths) != 1:
        raise _InvalidContentLengthError
    return lengths.pop()


def _declared_length_error(
    headers: Headers,
    limit: int,
    http_version: str,
) -> JSONResponse | None:
    if headers.getlist("content-length") and headers.getlist("transfer-encoding"):
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content={"detail": AMBIGUOUS_FRAMING_DETAIL},
            headers={"Connection": "close"}
            if http_version in HTTP_ONE_VERSIONS
            else None,
        )
    try:
        declared_length = _declared_content_length(headers)
    except _InvalidContentLengthError:
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content={"detail": INVALID_CONTENT_LENGTH_DETAIL},
        )
    if declared_length is not None and declared_length > limit:
        return _too_large_response()
    return None


def _too_large_response() -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        content={"detail": REQUEST_TOO_LARGE_DETAIL},
    )


def _request_id(headers: Headers) -> str:
    candidates = headers.getlist("x-request-id")
    if len(candidates) == 1 and SAFE_REQUEST_ID.fullmatch(candidates[0]):
        return candidates[0]
    return str(uuid4())
