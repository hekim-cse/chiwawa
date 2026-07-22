# Google Routes API를 이용한 추천 후보 경유 이동 지표 Provider
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import math

import httpx

from ai.free_time_recommender.domain.candidate_route_metrics import (
    CandidateRouteMetrics,
    CandidateRouteMetricsQuery,
    RouteLegMetrics,
)
from ai.free_time_recommender.providers.errors import (
    CandidateRouteMetricsHttpError,
    CandidateRouteMetricsTimeoutError,
    CandidateRouteMetricsTransportError,
    InvalidCandidateRouteMetricsResponseError,
)


class GoogleCandidateRouteMetricsProvider:
    """후보 전후의 두 경로를 시간 순서대로 계산한다."""

    BASE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
    FIELD_MASK = "routes.legs.duration,routes.legs.distanceMeters"

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
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds는 0보다 큰 유한한 값이어야 합니다."
            )
        self._api_key = api_key
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport

    def get_candidate_route_metrics(
        self,
        query: CandidateRouteMetricsQuery,
    ) -> CandidateRouteMetrics:
        """후보 도착과 체류를 반영해 두 경로를 순차 조회한다."""

        if not isinstance(query, CandidateRouteMetricsQuery):
            raise TypeError("query는 CandidateRouteMetricsQuery여야 합니다.")

        previous_to_candidate = self._get_leg_metrics(
            origin_place_id=query.previous_place_id,
            destination_place_id=query.candidate_place_id,
            departure_at=query.previous_departure_at,
            travel_mode=query.travel_mode.value,
        )
        candidate_arrival_at = query.previous_departure_at + timedelta(
            minutes=previous_to_candidate.travel_minutes
        )
        candidate_departure_at = candidate_arrival_at + timedelta(
            minutes=query.stay_minutes
        )
        candidate_to_next = self._get_leg_metrics(
            origin_place_id=query.candidate_place_id,
            destination_place_id=query.next_place_id,
            departure_at=candidate_departure_at,
            travel_mode=query.travel_mode.value,
        )
        next_arrival_at = candidate_departure_at + timedelta(
            minutes=candidate_to_next.travel_minutes
        )
        return CandidateRouteMetrics(
            previous_to_candidate=previous_to_candidate,
            candidate_to_next=candidate_to_next,
            candidate_arrival_at=candidate_arrival_at,
            candidate_departure_at=candidate_departure_at,
            next_arrival_at=next_arrival_at,
        )

    def _get_leg_metrics(
        self,
        *,
        origin_place_id: str,
        destination_place_id: str,
        departure_at: datetime,
        travel_mode: str,
    ) -> RouteLegMetrics:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": self.FIELD_MASK,
        }
        payload = {
            "origin": {"placeId": origin_place_id},
            "destination": {"placeId": destination_place_id},
            "travelMode": travel_mode,
            "departureTime": self._to_utc_text(departure_at),
            "computeAlternativeRoutes": False,
            "languageCode": "ko",
            "regionCode": "JP",
        }
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
            raise CandidateRouteMetricsTimeoutError(
                "Google Routes API 이동 지표 요청 시간이 초과됐습니다."
            ) from error
        except httpx.TransportError as error:
            raise CandidateRouteMetricsTransportError(
                "Google Routes API 이동 지표 네트워크 요청에 "
                "실패했습니다."
            ) from error
        if response.status_code >= 400:
            raise CandidateRouteMetricsHttpError(response.status_code)
        return self._parse_response(response)

    @staticmethod
    def _to_utc_text(value: datetime) -> str:
        return (
            value.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

    @classmethod
    def _parse_response(
        cls,
        response: httpx.Response,
    ) -> RouteLegMetrics:
        try:
            payload = response.json()
        except ValueError as error:
            raise InvalidCandidateRouteMetricsResponseError(
                "Google Routes API 이동 지표 응답이 JSON 형식이 아닙니다."
            ) from error
        if not isinstance(payload, dict):
            raise InvalidCandidateRouteMetricsResponseError(
                "Google Routes API 이동 지표 응답은 객체여야 합니다."
            )
        routes = payload.get("routes")
        if not isinstance(routes, list) or len(routes) != 1:
            raise InvalidCandidateRouteMetricsResponseError(
                "Google Routes API 이동 지표 응답에는 "
                "경로 하나가 필요합니다."
            )
        route = routes[0]
        if not isinstance(route, dict):
            raise InvalidCandidateRouteMetricsResponseError(
                "Google Routes API 경로 값은 객체여야 합니다."
            )
        legs = route.get("legs")
        if not isinstance(legs, list) or len(legs) != 1:
            raise InvalidCandidateRouteMetricsResponseError(
                "Google Routes API 경로에는 이동 구간 하나가 "
                "필요합니다."
            )
        leg = legs[0]
        if not isinstance(leg, dict):
            raise InvalidCandidateRouteMetricsResponseError(
                "Google Routes API 이동 구간은 객체여야 합니다."
            )
        try:
            travel_minutes = cls._duration_to_ceil_minutes(
                leg["duration"]
            )
            distance_meters = leg["distanceMeters"]
            return RouteLegMetrics(travel_minutes, distance_meters)
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidCandidateRouteMetricsResponseError(
                "Google Routes API 이동 구간 값이 유효하지 않습니다."
            ) from error

    @staticmethod
    def _duration_to_ceil_minutes(value: object) -> int:
        if not isinstance(value, str) or not value.endswith("s"):
            raise ValueError("duration은 초 단위 문자열이어야 합니다.")
        try:
            seconds = Decimal(value[:-1])
        except InvalidOperation as error:
            raise ValueError("duration 숫자가 유효하지 않습니다.") from error
        if not seconds.is_finite() or seconds < 0:
            raise ValueError(
                "duration은 0 이상의 유한한 값이어야 합니다."
            )
        return int((seconds / Decimal(60)).to_integral_value(ROUND_CEILING))
