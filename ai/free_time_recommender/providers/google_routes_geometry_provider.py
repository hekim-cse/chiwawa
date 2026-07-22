# Google Routes API를 이용한 경로 geometry Provider
from __future__ import annotations

from datetime import timezone
import math

import httpx

from ai.free_time_recommender.domain.route_geometry import (
    GeoCoordinate,
    RouteGeometryQuery,
    RouteLegGeometry,
)
from ai.free_time_recommender.providers.errors import (
    InvalidRouteGeometryResponseError,
    RouteGeometryHttpError,
    RouteGeometryTimeoutError,
    RouteGeometryTransportError,
)


class GoogleRoutesGeometryProvider:
    """Google Routes Compute Routes의 polyline 조회 구현."""

    BASE_URL = (
        "https://routes.googleapis.com/directions/v2:computeRoutes"
    )
    FIELD_MASK = "routes.polyline.encodedPolyline"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not isinstance(api_key, str):
            raise TypeError("api_key는 문자열이어야 합니다.")

        if not api_key.strip():
            raise ValueError("api_key는 비어 있을 수 없습니다.")

        if isinstance(timeout_seconds, bool) or not isinstance(
            timeout_seconds,
            (int, float),
        ):
            raise TypeError("timeout_seconds는 숫자여야 합니다.")

        if not math.isfinite(timeout_seconds):
            raise ValueError(
                "timeout_seconds는 유한한 값이어야 합니다."
            )

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds는 0보다 커야 합니다.")

        self._api_key = api_key
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport

    def get_route_geometry(
        self,
        query: RouteGeometryQuery,
    ) -> RouteLegGeometry:
        """조회 조건을 Google 요청으로 변환하고 내부 geometry를 반환한다."""

        if not isinstance(query, RouteGeometryQuery):
            raise TypeError("query는 RouteGeometryQuery여야 합니다.")

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": self.FIELD_MASK,
        }
        payload: dict[str, object] = {
            "origin": self._to_waypoint(query.origin),
            "destination": self._to_waypoint(query.destination),
            "travelMode": query.travel_mode.value,
            "computeAlternativeRoutes": False,
            "polylineQuality": "OVERVIEW",
            "polylineEncoding": "ENCODED_POLYLINE",
        }

        if query.departure_at is not None:
            payload["departureTime"] = (
                query.departure_at
                .astimezone(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
            # DRIVE에서 출발시각을 사용하려면 Google Routes의 기본값인
            # TRAFFIC_UNAWARE 대신 교통량을 반영하는 설정을 명시해야 한다.
            if query.travel_mode.value == "DRIVE":
                payload["routingPreference"] = "TRAFFIC_AWARE"

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as error:
            raise RouteGeometryTimeoutError(
                "Google Routes API 요청 시간이 초과됐습니다."
            ) from error
        except httpx.TransportError as error:
            raise RouteGeometryTransportError(
                "Google Routes API 네트워크 요청에 실패했습니다."
            ) from error

        if response.status_code >= 400:
            raise RouteGeometryHttpError(response.status_code)

        return self._parse_response(response)

    @staticmethod
    def _to_waypoint(coordinate: GeoCoordinate) -> dict[str, object]:
        return {
            "location": {
                "latLng": {
                    "latitude": coordinate.latitude,
                    "longitude": coordinate.longitude,
                }
            }
        }

    @staticmethod
    def _parse_response(response: httpx.Response) -> RouteLegGeometry:
        try:
            payload = response.json()
        except ValueError as error:
            raise InvalidRouteGeometryResponseError(
                "Google Routes API 응답이 JSON 형식이 아닙니다."
            ) from error

        if not isinstance(payload, dict):
            raise InvalidRouteGeometryResponseError(
                "Google Routes API 응답 최상위 값은 객체여야 합니다."
            )

        routes = payload.get("routes")
        if not isinstance(routes, list) or len(routes) != 1:
            raise InvalidRouteGeometryResponseError(
                "Google Routes API 응답에는 하나의 경로가 필요합니다."
            )

        route = routes[0]
        if not isinstance(route, dict):
            raise InvalidRouteGeometryResponseError(
                "Google Routes API 경로 값은 객체여야 합니다."
            )

        polyline = route.get("polyline")
        if not isinstance(polyline, dict):
            raise InvalidRouteGeometryResponseError(
                "Google Routes API 응답에 polyline이 없습니다."
            )

        encoded_polyline = polyline.get("encodedPolyline")
        if not isinstance(encoded_polyline, str) or not (
            encoded_polyline.strip()
        ):
            raise InvalidRouteGeometryResponseError(
                "Google Routes API 응답에 유효한 encodedPolyline이 "
                "없습니다."
            )

        return RouteLegGeometry(
            encoded_polyline=encoded_polyline,
        )
