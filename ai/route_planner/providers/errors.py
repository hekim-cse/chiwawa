# Google Routes Matrix Provider의 명시적 외부 연동 오류


class GoogleRoutesProviderError(RuntimeError):
    """Google Routes Matrix Provider 오류의 기반 타입."""


class GoogleRoutesTimeoutError(GoogleRoutesProviderError):
    """Google Routes Matrix 요청 제한시간 초과."""


class GoogleRoutesTransportError(GoogleRoutesProviderError):
    """Google Routes Matrix 네트워크 전송 실패."""


class GoogleRoutesHttpError(GoogleRoutesProviderError):
    """Google Routes Matrix HTTP 오류."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(
            "Google Routes API Matrix 요청에 실패했습니다. "
            f"status_code={status_code}"
        )


class InvalidGoogleRoutesResponseError(GoogleRoutesProviderError):
    """Google Routes Matrix 응답 계약 오류."""
