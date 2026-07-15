from http import HTTPStatus
from typing import assert_never

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from chiwawa_backend.errors import (
    ApplicationError,
    AuthenticationError,
    ConfigurationError,
    DomainValidationError,
    InsufficientStorageError,
    NotFoundError,
    PayloadTooLargeError,
    RateLimitError,
    ServiceUnavailableError,
    UnsupportedMediaTypeError,
    UpstreamServiceError,
)
from chiwawa_backend.middleware.request_security import hardened_response_headers
from chiwawa_backend.schemas.base import ErrorResponse

APPLICATION_ERROR_STATUS: tuple[
    tuple[type[ApplicationError], HTTPStatus],
    ...,
] = (
    (AuthenticationError, HTTPStatus.UNAUTHORIZED),
    (PayloadTooLargeError, HTTPStatus.CONTENT_TOO_LARGE),
    (UnsupportedMediaTypeError, HTTPStatus.UNSUPPORTED_MEDIA_TYPE),
    (RateLimitError, HTTPStatus.TOO_MANY_REQUESTS),
    (UpstreamServiceError, HTTPStatus.BAD_GATEWAY),
    (ServiceUnavailableError, HTTPStatus.SERVICE_UNAVAILABLE),
    (InsufficientStorageError, HTTPStatus.INSUFFICIENT_STORAGE),
    (ApplicationError, HTTPStatus.INTERNAL_SERVER_ERROR),
)
type DomainError = NotFoundError | DomainValidationError | ConfigurationError


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, _application_error_handler)
    app.add_exception_handler(NotFoundError, _domain_error_handler)
    app.add_exception_handler(DomainValidationError, _domain_error_handler)
    app.add_exception_handler(ConfigurationError, _domain_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)


async def _application_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    _ = request
    if not isinstance(exc, ApplicationError):
        raise exc
    return _error_response(
        _application_error_status(exc),
        str(exc),
        exc.headers,
    )


def _application_error_status(exc: ApplicationError) -> HTTPStatus:
    return next(
        status_code
        for error_type, status_code in APPLICATION_ERROR_STATUS
        if isinstance(exc, error_type)
    )


async def _domain_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    _ = request
    if not isinstance(
        exc,
        NotFoundError | DomainValidationError | ConfigurationError,
    ):
        raise exc
    return _error_response(_domain_error_status(exc), str(exc))


def _domain_error_status(exc: DomainError) -> HTTPStatus:
    match exc:
        case NotFoundError():
            return HTTPStatus.NOT_FOUND
        case DomainValidationError():
            return HTTPStatus.UNPROCESSABLE_ENTITY
        case ConfigurationError():
            return HTTPStatus.INTERNAL_SERVER_ERROR
        case _:
            assert_never(exc)


async def _http_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    _ = request
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    headers = None if exc.headers is None else dict(exc.headers)
    return _error_response(exc.status_code, str(exc.detail), headers)


async def _validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    _ = request
    if not isinstance(exc, RequestValidationError):
        raise exc
    return _error_response(
        HTTPStatus.UNPROCESSABLE_ENTITY,
        "request validation failed",
    )


async def _unexpected_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    _ = exc
    return _error_response(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "internal server error",
        hardened_response_headers(request.headers, request.url.path),
    )


def _error_response(
    status_code: int,
    detail: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error = ErrorResponse(detail=detail)
    return JSONResponse(
        status_code=status_code,
        content=error.model_dump(),
        headers=headers,
    )
