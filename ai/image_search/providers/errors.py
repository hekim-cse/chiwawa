# 이미지 검색 외부 연동 provider(Cloud Vision · Gemini · Places)의 명시적 오류
# RuntimeError 를 기반으로 둬, modal_app 의 502 매핑과 recognizer 의 우아한 저하가 그대로 동작한다.


class ProviderError(RuntimeError):
    """이미지 검색 외부 provider 오류의 기반 타입."""


class ProviderTimeoutError(ProviderError):
    """외부 provider 요청 제한시간 초과."""


class ProviderTransportError(ProviderError):
    """외부 provider 네트워크 전송 실패."""


class ProviderHttpError(ProviderError):
    """외부 provider HTTP 오류."""

    def __init__(self, provider: str, status_code: int) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(
            f"{provider} API 요청에 실패했습니다. status_code={status_code}"
        )


class InvalidProviderResponseError(ProviderError):
    """외부 provider 응답 계약 오류."""
