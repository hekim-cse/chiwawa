# Google Routes API의 장소 좌표 Matrix를
# 내부 이동시간 모델로 변환하는 Provider
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import math
from typing import Optional

import httpx

from ai.route_planner.domain.schemas import (
    Location,
    TravelMode,
    TravelTimeElement,
    TravelTimeMatrix,
    TravelTimeMatrixResult,
)
from ai.route_planner.providers.env import get_google_maps_api_key
from ai.route_planner.providers.errors import (
    GoogleRoutesHttpError,
    GoogleRoutesTimeoutError,
    GoogleRoutesTransportError,
    InvalidGoogleRoutesResponseError,
)


class GoogleRoutesProvider:
    """Google Compute Route Matrix를 호출하는 운영 Provider."""

    BASE_URL = (
        "https://routes.googleapis.com/"
        "distanceMatrix/v2:computeRouteMatrix"
    )
    FIELD_MASK = (
        "originIndex,destinationIndex,duration,distanceMeters,"
        "status,condition"
    )
    DEFAULT_MAX_ELEMENTS = 625
    TRANSIT_MAX_ELEMENTS = 100

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        resolved_api_key = (
            get_google_maps_api_key() if api_key is None else api_key
        )
        if not isinstance(resolved_api_key, str):
            raise TypeError("api_key는 문자열이어야 합니다.")
        if not resolved_api_key.strip():
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

        self._api_key = resolved_api_key
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport

    def build_travel_time_matrix_result(
        self,
        locations: list[Location],
        travel_mode: TravelMode = TravelMode.TRANSIT,
        departure_time: datetime | None = None,
    ) -> TravelTimeMatrixResult:
        """정상 이동 구간과 계산하지 못한 구간을 분리한다."""

        elements = self.compute_route_matrix(
            locations=locations,
            travel_mode=travel_mode,
            departure_time=departure_time,
        )
        matrix: TravelTimeMatrix = {}
        missing_elements: list[TravelTimeElement] = []

        for element in elements:
            if element.origin_index == element.destination_index:
                continue
            if element.duration_minutes is None:
                missing_elements.append(element)
                continue
            matrix[(element.origin_name, element.destination_name)] = (
                element.duration_minutes
            )

        return TravelTimeMatrixResult(
            matrix=matrix,
            missing_elements=missing_elements,
        )

    def build_travel_time_matrix(
        self,
        locations: list[Location],
        travel_mode: TravelMode = TravelMode.TRANSIT,
        departure_time: datetime | None = None,
    ) -> TravelTimeMatrix:
        """기존 호출부에 정상 이동시간 Matrix만 제공한다."""

        return self.build_travel_time_matrix_result(
            locations=locations,
            travel_mode=travel_mode,
            departure_time=departure_time,
        ).matrix

    def compute_route_matrix(
        self,
        locations: list[Location],
        travel_mode: TravelMode = TravelMode.TRANSIT,
        departure_time: datetime | None = None,
    ) -> list[TravelTimeElement]:
        """입력을 검증하고 실제 Google Routes Matrix를 조회한다."""

        self._validate_request(locations, travel_mode, departure_time)
        payload = self._build_payload(
            locations=locations,
            travel_mode=travel_mode,
            departure_time=departure_time,
        )
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": self.FIELD_MASK,
        }
        client_arguments: dict[str, object] = {
            "timeout": self._timeout_seconds,
        }
        if self._transport is not None:
            client_arguments["transport"] = self._transport

        try:
            with httpx.Client(**client_arguments) as client:
                response = client.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as error:
            raise GoogleRoutesTimeoutError(
                "Google Routes API Matrix 요청 시간이 초과됐습니다."
            ) from error
        except httpx.TransportError as error:
            raise GoogleRoutesTransportError(
                "Google Routes API Matrix 네트워크 요청에 실패했습니다."
            ) from error

        if response.status_code >= 400:
            raise GoogleRoutesHttpError(response.status_code)
        return self._parse_response(response, locations)

    def _validate_request(
        self,
        locations: list[Location],
        travel_mode: TravelMode,
        departure_time: datetime | None,
    ) -> None:
        if not isinstance(locations, list):
            raise TypeError("locations는 list여야 합니다.")
        if len(locations) < 2:
            raise ValueError(
                "locations는 두 개 이상의 장소가 필요합니다."
            )
        if any(not isinstance(location, Location) for location in locations):
            raise TypeError("locations는 Location만 포함해야 합니다.")
        if not isinstance(travel_mode, TravelMode):
            raise TypeError("travel_mode는 TravelMode여야 합니다.")

        element_count = len(locations) * len(locations)
        maximum_elements = (
            self.TRANSIT_MAX_ELEMENTS
            if travel_mode is TravelMode.TRANSIT
            else self.DEFAULT_MAX_ELEMENTS
        )
        if element_count > maximum_elements:
            raise ValueError(
                "Google Routes Matrix 요청 크기 제한을 초과했습니다. "
                f"travel_mode={travel_mode.value}, "
                f"element_count={element_count}, "
                f"maximum_elements={maximum_elements}"
            )

        if departure_time is not None:
            if not isinstance(departure_time, datetime):
                raise TypeError("departure_time은 datetime이어야 합니다.")
            if (
                departure_time.tzinfo is None
                or departure_time.utcoffset() is None
            ):
                raise ValueError(
                    "departure_time은 timezone-aware datetime이어야 합니다."
                )

    @classmethod
    def _build_payload(
        cls,
        *,
        locations: list[Location],
        travel_mode: TravelMode,
        departure_time: datetime | None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "origins": [
                cls._to_route_matrix_location(location)
                for location in locations
            ],
            "destinations": [
                cls._to_route_matrix_location(location)
                for location in locations
            ],
            "travelMode": travel_mode.value,
        }
        if travel_mode is TravelMode.DRIVE:
            payload["routingPreference"] = "TRAFFIC_AWARE"
        if (
            travel_mode in (TravelMode.DRIVE, TravelMode.TRANSIT)
            and departure_time is not None
        ):
            payload["departureTime"] = cls._to_utc_text(departure_time)
        return payload

    @staticmethod
    def _to_utc_text(value: datetime) -> str:
        return (
            value.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

    @staticmethod
    def _to_route_matrix_location(location: Location) -> dict[str, object]:
        return {
            "waypoint": {
                "location": {
                    "latLng": {
                        "latitude": location.lat,
                        "longitude": location.lng,
                    }
                }
            }
        }

    @classmethod
    def _parse_response(
        cls,
        response: httpx.Response,
        locations: list[Location],
    ) -> list[TravelTimeElement]:
        try:
            payload = response.json()
        except ValueError as error:
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API Matrix 응답이 JSON 형식이 아닙니다."
            ) from error
        if not isinstance(payload, list):
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API Matrix 응답은 배열이어야 합니다."
            )

        elements = [
            cls._parse_element(element, locations)
            for element in payload
        ]
        actual_pairs = {
            (element.origin_index, element.destination_index)
            for element in elements
        }
        expected_pairs = {
            (origin_index, destination_index)
            for origin_index in range(len(locations))
            for destination_index in range(len(locations))
        }
        if len(actual_pairs) != len(elements):
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API Matrix 응답 구간이 중복됐습니다."
            )
        if actual_pairs != expected_pairs:
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API Matrix 응답 구간이 완전하지 않습니다."
            )
        return elements

    @classmethod
    def _parse_element(
        cls,
        element: object,
        locations: list[Location],
    ) -> TravelTimeElement:
        if not isinstance(element, dict):
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API Matrix element는 객체여야 합니다."
            )
        origin_index = cls._parse_index(
            element.get("originIndex"),
            "originIndex",
            len(locations),
        )
        destination_index = cls._parse_index(
            element.get("destinationIndex"),
            "destinationIndex",
            len(locations),
        )
        distance_meters = element.get("distanceMeters")
        if (
            distance_meters is not None
            and (
                isinstance(distance_meters, bool)
                or not isinstance(distance_meters, int)
                or distance_meters < 0
            )
        ):
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API distanceMeters가 유효하지 않습니다."
            )
        status = element.get("status")
        if status is not None and not isinstance(status, dict):
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API status가 유효하지 않습니다."
            )
        status_code = status.get("code") if status is not None else None
        if (
            status_code is not None
            and (
                isinstance(status_code, bool)
                or not isinstance(status_code, (int, str))
            )
        ):
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API status.code가 유효하지 않습니다."
            )
        condition = element.get("condition")
        if condition is not None and not isinstance(condition, str):
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API condition이 유효하지 않습니다."
            )

        return TravelTimeElement(
            origin_name=locations[origin_index].name,
            destination_name=locations[destination_index].name,
            origin_index=origin_index,
            destination_index=destination_index,
            duration_seconds=cls._parse_duration_seconds(
                element.get("duration")
            ),
            distance_meters=distance_meters,
            status=(str(status_code) if status_code is not None else None),
            condition=condition,
        )

    @staticmethod
    def _parse_index(value: object, name: str, location_count: int) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value < location_count
        ):
            raise InvalidGoogleRoutesResponseError(
                f"Google Routes API {name}가 유효하지 않습니다."
            )
        return value

    @staticmethod
    def _parse_duration_seconds(value: object) -> Optional[int]:
        if value is None:
            return None
        if not isinstance(value, str) or not value.endswith("s"):
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API duration 형식이 유효하지 않습니다."
            )
        try:
            seconds = Decimal(value[:-1])
        except InvalidOperation as error:
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API duration 숫자가 유효하지 않습니다."
            ) from error
        if not seconds.is_finite() or seconds < 0:
            raise InvalidGoogleRoutesResponseError(
                "Google Routes API duration은 0 이상의 "
                "유한한 값이어야 합니다."
            )
        return int(seconds.to_integral_value(rounding=ROUND_CEILING))
