# 빈 시간대 추천 외부 Provider 오류 정의


class RouteGeometryProviderError(RuntimeError):
    """경로 geometry Provider의 기본 오류."""


class RouteGeometryTimeoutError(RouteGeometryProviderError):
    """경로 geometry 요청 제한시간 초과 오류."""


class RouteGeometryTransportError(RouteGeometryProviderError):
    """경로 geometry 네트워크 전송 오류."""


class RouteGeometryHttpError(RouteGeometryProviderError):
    """경로 geometry HTTP 응답 오류."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(
            "Google Routes API 요청에 실패했습니다. "
            f"status_code={status_code}"
        )


class InvalidRouteGeometryResponseError(RouteGeometryProviderError):
    """경로 geometry 응답 계약 오류."""
