from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.errors import (
    ApplicationError,
    AuthenticationError,
    InsufficientStorageError,
    PayloadTooLargeError,
    RateLimitError,
    ServiceUnavailableError,
    UnsupportedMediaTypeError,
    UpstreamServiceError,
)
from chiwawa_backend.main import create_app
from tests.memorial_test_support import settings

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _error_endpoint(error: ApplicationError) -> Callable[[], None]:
    def endpoint() -> None:
        raise error

    return endpoint


class DerivedAuthenticationError(AuthenticationError):
    pass


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (AuthenticationError("authentication failed"), HTTPStatus.UNAUTHORIZED),
        (
            DerivedAuthenticationError("derived authentication failed"),
            HTTPStatus.UNAUTHORIZED,
        ),
        (PayloadTooLargeError("payload too large"), HTTPStatus.CONTENT_TOO_LARGE),
        (
            UnsupportedMediaTypeError("unsupported media"),
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        ),
        (RateLimitError("rate limited"), HTTPStatus.TOO_MANY_REQUESTS),
        (UpstreamServiceError("upstream failed"), HTTPStatus.BAD_GATEWAY),
        (
            ServiceUnavailableError("service unavailable"),
            HTTPStatus.SERVICE_UNAVAILABLE,
        ),
        (
            InsufficientStorageError("storage unavailable"),
            HTTPStatus.INSUFFICIENT_STORAGE,
        ),
    ],
)
async def test_application_errors_have_central_http_mapping(
    tmp_path: Path,
    error: ApplicationError,
    expected_status: HTTPStatus,
) -> None:
    app = create_app(settings=settings(tmp_path))
    app.add_api_route("/error-probe", _error_endpoint(error), methods=["GET"])

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/error-probe")

    assert response.status_code == expected_status
    assert response.json() == {"detail": str(error)}


@pytest.mark.anyio
async def test_rate_limit_error_preserves_retry_after(tmp_path: Path) -> None:
    app = create_app(settings=settings(tmp_path))
    error = RateLimitError("rate limited", retry_after=17)
    app.add_api_route("/rate-probe", _error_endpoint(error), methods=["GET"])

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/rate-probe")

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert response.headers["retry-after"] == "17"


@pytest.mark.anyio
async def test_request_validation_error_is_normalized(tmp_path: Path) -> None:
    app = create_app(settings=settings(tmp_path))

    def validation_probe(value: int) -> int:
        return value

    app.add_api_route("/validation-probe/{value}", validation_probe, methods=["GET"])
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/validation-probe/not-an-integer")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == {"detail": "request validation failed"}


@pytest.mark.anyio
async def test_unexpected_exception_is_normalized_as_json(tmp_path: Path) -> None:
    app = create_app(settings=settings(tmp_path))

    def unexpected_error() -> None:
        message = "private diagnostic"
        raise RuntimeError(message)

    app.add_api_route("/unexpected-error", unexpected_error, methods=["GET"])
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/unexpected-error",
            headers={"X-Request-ID": "error-trace"},
        )

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-request-id"] == "error-trace"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.json() == {"detail": "internal server error"}


@pytest.mark.anyio
async def test_structured_http_exception_is_normalized_as_string(
    tmp_path: Path,
) -> None:
    app = create_app(settings=settings(tmp_path))

    def structured_error() -> None:
        raise HTTPException(
            status_code=HTTPStatus.IM_A_TEAPOT,
            detail={"reason": "teapot"},
            headers={"X-Tea": "oolong"},
        )

    app.add_api_route("/structured-error", structured_error, methods=["GET"])
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/structured-error")

    assert response.status_code == HTTPStatus.IM_A_TEAPOT
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-tea"] == "oolong"
    assert response.json() == {"detail": "{'reason': 'teapot'}"}
