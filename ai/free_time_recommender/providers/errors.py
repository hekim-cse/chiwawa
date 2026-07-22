# 경로 geometry와 경로 주변 장소 Provider의 명시적 오류


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


class AlongRoutePlaceProviderError(RuntimeError):
    """경로 주변 장소 Provider 오류의 기반 타입."""


class AlongRoutePlaceTimeoutError(AlongRoutePlaceProviderError):
    """Google Places 요청 제한시간 초과."""


class AlongRoutePlaceTransportError(AlongRoutePlaceProviderError):
    """Google Places 네트워크 전송 실패."""


class AlongRoutePlaceHttpError(AlongRoutePlaceProviderError):
    """Google Places가 오류 HTTP 상태를 반환함."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(
            "Google Places API 요청에 실패했습니다. "
            f"status_code={status_code}"
        )


class InvalidAlongRoutePlaceResponseError(AlongRoutePlaceProviderError):
    """Google Places 응답이 내부 계약을 충족하지 않음."""
