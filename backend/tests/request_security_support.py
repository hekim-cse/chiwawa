from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal, NotRequired, TypedDict

from httpx import ASGITransport, AsyncClient, Response
from pydantic import SecretStr, TypeAdapter

from chiwawa_backend.config import Settings
from chiwawa_backend.services.jwt_auth import create_access_token

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class _ResponseStartMessage(TypedDict):
    type: Literal["http.response.start"]
    status: int
    headers: NotRequired[list[tuple[bytes, bytes]]]


class _ResponseBodyMessage(TypedDict):
    type: Literal["http.response.body"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


RESPONSE_START_ADAPTER: Final = TypeAdapter(_ResponseStartMessage)
RESPONSE_BODY_ADAPTER: Final = TypeAdapter(_ResponseBodyMessage)


@dataclass(slots=True)  # noqa: RUF100  # noqa: MUTABLE_OK
class ASGIProbe:
    """Mutable request-boundary counters for direct ASGI observations."""

    app: ASGIApp
    receive_calls: int = 0
    response_starts: int = 0
    terminal_bodies: int = 0
    status_code: int | None = None
    response_headers: list[tuple[bytes, bytes]] | None = None
    response_body: bytes = b""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def counted_receive() -> Message:
            self.receive_calls += 1
            return await receive()

        async def counted_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_start = RESPONSE_START_ADAPTER.validate_python(
                    message,
                    strict=True,
                )
                self.response_starts += 1
                self.status_code = response_start["status"]
                self.response_headers = response_start.get("headers", [])
            if message["type"] == "http.response.body":
                response_body = RESPONSE_BODY_ADAPTER.validate_python(
                    message,
                    strict=True,
                )
                if not response_body.get("more_body", False):
                    self.terminal_bodies += 1
                self.response_body += response_body.get("body", b"")
            await send(message)

        await self.app(scope, counted_receive, counted_send)


def request_settings(*, json_limit: int = 5, multipart_limit: int = 5) -> Settings:
    return Settings(
        jwt_secret=SecretStr("request-security-test-secret-at-least-32-characters"),
        max_json_body_bytes=json_limit,
        max_multipart_body_bytes=multipart_limit,
    )


async def request_chunks(parts: Sequence[bytes]) -> AsyncIterator[bytes]:
    for part in parts:
        yield part


def access_token(settings: Settings) -> str:
    return create_access_token("1", settings=settings)


async def request_with_chunks(
    probe: ASGIProbe,
    method: str,
    path: str,
    *,
    headers: Sequence[tuple[str, str]] = (),
    chunks: Sequence[bytes] = (),
) -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=probe),
        base_url="http://test",
    ) as client:
        return await client.request(
            method,
            path,
            headers=headers,
            content=request_chunks(chunks),
        )


def http_scope(
    headers: Sequence[tuple[bytes, bytes]] = (),
    *,
    http_version: str = "1.1",
) -> Scope:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": http_version,
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/trips",
        "raw_path": b"/api/v1/trips",
        "query_string": b"",
        "root_path": "",
        "headers": list(headers),
        "client": ("127.0.0.1", 50000),
        "server": ("test", 80),
        "state": {},
    }


async def discard_send(_message: Message) -> None:
    return
