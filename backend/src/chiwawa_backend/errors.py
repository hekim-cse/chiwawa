from dataclasses import dataclass
from typing import override


class ApplicationError(RuntimeError):
    detail: str
    headers: dict[str, str] | None

    def __init__(
        self,
        detail: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.headers = headers

    @override
    def __str__(self) -> str:
        return self.detail


class AuthenticationError(ApplicationError):
    pass


class PayloadTooLargeError(ApplicationError):
    pass


class UnsupportedMediaTypeError(ApplicationError):
    pass


class RateLimitError(ApplicationError):
    def __init__(self, detail: str, *, retry_after: int | None = None) -> None:
        headers = None if retry_after is None else {"Retry-After": str(retry_after)}
        super().__init__(detail, headers=headers)


class UpstreamServiceError(ApplicationError):
    pass


class ServiceUnavailableError(ApplicationError):
    pass


class InsufficientStorageError(ApplicationError):
    pass


@dataclass(slots=True)  # noqa: RUF100  # noqa: MUTABLE_OK
class NotFoundError(Exception):
    """Mutable because Python attaches traceback state while unwinding contexts."""

    entity: str
    entity_id: str

    @override
    def __str__(self) -> str:
        return f"{self.entity} {self.entity_id} not found"


@dataclass(slots=True)  # noqa: RUF100  # noqa: MUTABLE_OK
class DomainValidationError(ValueError):
    """Mutable because Python attaches traceback state while unwinding contexts."""

    detail: str

    @override
    def __str__(self) -> str:
        return self.detail


@dataclass(slots=True)  # noqa: RUF100  # noqa: MUTABLE_OK
class ConfigurationError(RuntimeError):
    """Mutable because Python attaches traceback state while unwinding contexts."""

    detail: str

    @override
    def __str__(self) -> str:
        return self.detail
