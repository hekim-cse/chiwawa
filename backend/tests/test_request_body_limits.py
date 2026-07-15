from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from chiwawa_backend.main import create_app
from chiwawa_backend.middleware import RequestBodyLimitMiddleware
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

    from starlette.types import Message, Receive, Scope, Send


@pytest.mark.anyio
async def test_oversized_declared_upload_is_rejected_before_body_receive(
    tmp_path: Path,
) -> None:
    # Given: an authenticated multipart request declares more than the configured limit.
    settings = request_settings(multipart_limit=5).model_copy(
        update={"google_auth_db_path": tmp_path / "app.db"},
    )
    _ = save_or_update_user(GoogleUserProfile(sub="body-user"), settings=settings)
    probe = ASGIProbe(create_app(state=AppState(), settings=settings))

    # When: the request reaches the body admission boundary.
    response = await request_with_chunks(
        probe,
        "POST",
        "/api/v1/memorial/photos",
        headers=(
            ("Authorization", f"Bearer {access_token(settings)}"),
            ("Content-Type", "MuLtIpArT/FoRm-DaTa; boundary=test"),
            ("Content-Length", "6"),
        ),
        chunks=(b"abcdef",),
    )

    # Then: declared size is rejected without asking the server for request bytes.
    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert response.json() == {"detail": "request body is too large"}
    assert probe.receive_calls == 0


@pytest.mark.anyio
async def test_chunked_multipart_stops_at_actual_limit_with_one_response(
    tmp_path: Path,
) -> None:
    # Given: an authenticated multipart stream crosses its limit mid-stream.
    settings = request_settings(multipart_limit=5).model_copy(
        update={"google_auth_db_path": tmp_path / "app.db"},
    )
    _ = save_or_update_user(GoogleUserProfile(sub="body-user"), settings=settings)
    probe = ASGIProbe(create_app(state=AppState(), settings=settings))

    # When: request parsing asks for the chunk that crosses the configured byte ceiling.
    response = await request_with_chunks(
        probe,
        "POST",
        "/api/v1/memorial/photos",
        headers=(
            ("Authorization", f"Bearer {access_token(settings)}"),
            ("Content-Type", "multipart/form-data; boundary=test"),
        ),
        chunks=(b"--tes", b"t\r\n", b"unconsumed"),
    )

    # Then: the tail is untouched and exactly one terminal HTTP response is emitted.
    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert probe.receive_calls == 2
    assert probe.response_starts == 1
    assert probe.terminal_bodies == 1


@pytest.mark.anyio
async def test_chunked_json_stops_at_actual_limit_with_one_response() -> None:
    # Given: a structured-suffix JSON stream crosses its smaller JSON limit.
    settings = request_settings(json_limit=5, multipart_limit=50)
    probe = ASGIProbe(create_app(state=AppState(), settings=settings))

    # When: the route parser receives the first over-limit chunk.
    response = await request_with_chunks(
        probe,
        "POST",
        "/api/v1/trips",
        headers=(("Content-Type", "Application/Problem+JSON; Charset=UTF-8"),),
        chunks=(b'{"ci', b'ty":', b'"Tokyo"}'),
    )

    # Then: JSON uses its own limit and emits no competing error response.
    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert probe.receive_calls == 2
    assert probe.response_starts == 1
    assert probe.terminal_bodies == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    "content_lengths",
    [("-1",), ("invalid",), ("5", "6"), ("5, 6",)],
)
async def test_invalid_content_length_is_rejected_safely(
    content_lengths: tuple[str, ...],
) -> None:
    # Given: a request contains a malformed, negative, or conflicting declared length.
    settings = request_settings(json_limit=50)
    probe = ASGIProbe(create_app(state=AppState(), settings=settings))
    headers = [("Content-Type", "application/json")]
    headers.extend(("Content-Length", value) for value in content_lengths)

    # When: the declared length is parsed at the ASGI boundary.
    response = await request_with_chunks(
        probe,
        "POST",
        "/api/v1/trips",
        headers=headers,
        chunks=(b"{}",),
    )

    # Then: the bad framing is a client error and no body is consumed.
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "invalid content-length"}
    assert probe.receive_calls == 0


@pytest.mark.anyio
async def test_overflow_after_response_start_completes_one_terminal_body() -> None:
    # Given: a downstream app starts 200 before reading an over-limit body chunk.
    async def start_then_receive(
        _scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        await send({"type": "http.response.start", "status": HTTPStatus.OK})
        _ = await receive()

    async def oversized_receive() -> Message:
        return {"type": "http.request", "body": b"abcdef", "more_body": False}

    middleware = RequestBodyLimitMiddleware(start_then_receive, 5, 50)
    probe = ASGIProbe(middleware)

    # When: the next receive crosses the configured JSON limit.
    await probe(http_scope(), oversized_receive, discard_send)

    # Then: status remains 200 and one empty terminal frame closes the response.
    assert probe.response_starts == 1
    assert probe.terminal_bodies == 1
    assert probe.response_body == b""


@pytest.mark.anyio
async def test_overflow_suppresses_downstream_sends_after_fail_closed_body() -> None:
    # Given: downstream cleanup attempts another response after receive overflows.
    async def start_receive_then_send(
        _scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        await send({"type": "http.response.start", "status": HTTPStatus.OK})
        try:
            _ = await receive()
        finally:
            await send({"type": "http.response.start", "status": HTTPStatus.CREATED})
            await send(
                {"type": "http.response.body", "body": b"leak", "more_body": False},
            )

    async def oversized_receive() -> Message:
        return {"type": "http.request", "body": b"abcdef", "more_body": False}

    middleware = RequestBodyLimitMiddleware(start_receive_then_send, 5, 50)
    probe = ASGIProbe(middleware)

    # When: the guarded receive closes the response at the byte limit.
    await probe(http_scope(), oversized_receive, discard_send)

    # Then: no second start or downstream terminal frame escapes the guard.
    assert probe.response_starts == 1
    assert probe.terminal_bodies == 1
    assert probe.response_body == b""
