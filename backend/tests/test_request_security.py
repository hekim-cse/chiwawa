from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import UUID

import anyio
import pytest
from starlette.responses import Response

from chiwawa_backend.main import create_app
from chiwawa_backend.middleware import EarlyUploadAuthMiddleware
from chiwawa_backend.schemas.auth import GoogleUserProfile
from chiwawa_backend.services.auth import save_or_update_user
from chiwawa_backend.state import AppState
from tests.request_security_support import (
    ASGIProbe,
    access_token,
    discard_send,
    http_scope,
    request_settings,
    request_with_chunks,
)

if TYPE_CHECKING:
    from pathlib import Path

    from httpx import Response as HTTPXResponse
    from starlette.types import Message, Receive, Scope, Send


@pytest.mark.anyio
async def test_shared_upload_slot_rejects_before_body_receive(
    tmp_path: Path,
) -> None:
    # Given: one worker holds the only shared upload request slot.
    active_settings = request_settings().model_copy(
        update={
            "google_auth_db_path": tmp_path / "app.db",
            "max_concurrent_uploads": 1,
            "max_concurrent_uploads_per_user": 1,
        },
    )
    _ = save_or_update_user(
        GoogleUserProfile(sub="request-slot-user"),
        settings=active_settings,
    )
    entered = anyio.Event()
    release = anyio.Event()

    async def blocked_app(scope: Scope, receive: Receive, send: Send) -> None:
        _ = receive
        entered.set()
        await release.wait()
        await Response(status_code=HTTPStatus.NO_CONTENT)(scope, receive, send)

    first = ASGIProbe(EarlyUploadAuthMiddleware(blocked_app, active_settings))
    second = ASGIProbe(EarlyUploadAuthMiddleware(blocked_app, active_settings))
    authorization = ("Authorization", f"Bearer {access_token(active_settings)}")
    first_responses: list[HTTPXResponse] = []
    rejected: HTTPXResponse | None = None

    async def hold_first_request() -> None:
        first_responses.append(
            await request_with_chunks(
                first,
                "POST",
                "/api/v1/memorial/photos",
                headers=(authorization,),
                chunks=(b"first-body",),
            ),
        )

    # When: another worker receives an authenticated upload at capacity.
    async with anyio.create_task_group() as task_group:
        _ = task_group.start_soon(hold_first_request)
        await entered.wait()
        rejected = await request_with_chunks(
            second,
            "POST",
            "/api/v1/memorial/photos",
            headers=(authorization,),
            chunks=(b"must-not-be-read",),
        )
        release.set()

    # Then: SQLite-wide admission returns 429 without parsing its multipart body.
    assert rejected is not None
    assert rejected.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert rejected.json() == {"detail": "global upload concurrency limit exceeded"}
    assert second.receive_calls == 0
    assert first_responses[0].status_code == HTTPStatus.NO_CONTENT


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    ["/api/v1/memorial/photos", "/api/v1/memorial/photos/"],
)
async def test_anonymous_upload_is_rejected_before_body_receive(path: str) -> None:
    # Given: an anonymous upload with an observable ASGI body.
    settings = request_settings()
    probe = ASGIProbe(create_app(state=AppState(), settings=settings))

    # When: the protected upload is attempted, including its optional trailing slash.
    response = await request_with_chunks(
        probe,
        "POST",
        path,
        headers=(("Content-Type", "multipart/form-data; boundary=test"),),
        chunks=(b"body-must-not-be-read",),
    )

    # Then: existing JWT semantics win without consuming a body byte.
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {"detail": "missing token"}
    assert probe.receive_calls == 0


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "path", "headers", "chunks", "expected_status"),
    [
        ("GET", "/health", (), (), HTTPStatus.OK),
        (
            "POST",
            "/api/v1/memorial/photos",
            (("Content-Type", "multipart/form-data; boundary=test"),),
            (b"body-must-not-be-read",),
            HTTPStatus.UNAUTHORIZED,
        ),
        ("GET", "/does-not-exist", (), (), HTTPStatus.NOT_FOUND),
        (
            "POST",
            "/api/v1/trips",
            (("Content-Type", "application/json"), ("Content-Length", "6")),
            (b"abcdef",),
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        ),
    ],
)
async def test_security_headers_exist_on_every_terminal_status(
    method: str,
    path: str,
    headers: tuple[tuple[str, str], ...],
    chunks: tuple[bytes, ...],
    expected_status: HTTPStatus,
) -> None:
    # Given: a client supplies a bounded safe correlation ID.
    settings = request_settings(json_limit=5)
    probe = ASGIProbe(create_app(state=AppState(), settings=settings))
    request_headers = (*headers, ("X-Request-ID", "trace_ABC-123.9"))

    # When: success and common error paths produce their terminal response.
    response = await request_with_chunks(
        probe,
        method,
        path,
        headers=request_headers,
        chunks=chunks,
    )

    # Then: the same stable request and browser hardening headers are always present.
    assert response.status_code == expected_status
    assert response.headers["x-request-id"] == "trace_ABC-123.9"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["content-security-policy"] == (
        "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    )


@pytest.mark.anyio
async def test_unsafe_request_id_is_replaced_with_uuid() -> None:
    # Given: a client correlation value exceeds the accepted bounded character policy.
    settings = request_settings()
    probe = ASGIProbe(create_app(state=AppState(), settings=settings))

    # When: the request passes through the outer security boundary.
    response = await request_with_chunks(
        probe,
        "GET",
        "/health",
        headers=(("X-Request-ID", "x" * 65),),
    )

    # Then: an application UUID replaces the unsafe value.
    assert UUID(response.headers["x-request-id"]).version == 4


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("http_version", "expected_connection"),
    [("1.0", b"close"), ("1.1", b"close"), ("2", None)],
)
async def test_content_length_with_transfer_encoding_is_rejected_before_receive(
    http_version: str,
    expected_connection: bytes | None,
) -> None:
    # Given: repeated mixed-case framing headers make the ASGI request ambiguous.
    settings = request_settings(json_limit=50)
    probe = ASGIProbe(create_app(state=AppState(), settings=settings))

    async def body_receive() -> Message:
        return {"type": "http.request", "body": b"{}", "more_body": False}

    scope = http_scope(
        (
            (b"Content-Type", b"application/json"),
            (b"Content-Length", b"2"),
            (b"content-length", b"2"),
            (b"TRANSFER-ENCODING", b"chunked"),
            (b"X-Request-ID", b"smuggle-test"),
        ),
        http_version=http_version,
    )

    # When: the assembled application inspects framing before route parsing.
    await probe(scope, body_receive, discard_send)

    # Then: it returns one hardened 400 without consuming a body message.
    assert probe.receive_calls == 0
    assert probe.response_starts == 1
    assert probe.terminal_bodies == 1
    assert probe.status_code == HTTPStatus.BAD_REQUEST
    assert probe.response_headers is not None
    response_headers = dict(probe.response_headers)
    assert response_headers[b"x-request-id"] == b"smuggle-test"
    assert response_headers[b"x-content-type-options"] == b"nosniff"
    assert response_headers[b"x-frame-options"] == b"DENY"
    assert response_headers[b"referrer-policy"] == b"no-referrer"
    assert response_headers.get(b"connection") == expected_connection
    assert probe.response_body == b'{"detail":"ambiguous request framing"}'
