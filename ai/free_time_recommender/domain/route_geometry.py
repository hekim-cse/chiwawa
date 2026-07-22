# 경로 주변 추천 검색에 사용할 순수 경로 geometry 도메인
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math


class RouteTravelMode(str, Enum):
    """경로 geometry 계산에 사용할 이동 방식."""

    WALK = "WALK"
    DRIVE = "DRIVE"
    TRANSIT = "TRANSIT"


@dataclass(frozen=True)
class GeoCoordinate:
    """외부 지도 SDK에 의존하지 않는 위도·경도 좌표."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        self._validate_coordinate(
            self.latitude,
            "latitude",
            minimum=-90.0,
            maximum=90.0,
        )
        self._validate_coordinate(
            self.longitude,
            "longitude",
            minimum=-180.0,
            maximum=180.0,
        )

    @staticmethod
    def _validate_coordinate(
        value: float,
        field_name: str,
        *,
        minimum: float,
        maximum: float,
    ) -> None:
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise TypeError(f"{field_name}는 숫자여야 합니다.")

        if not math.isfinite(value):
            raise ValueError(f"{field_name}는 유한한 값이어야 합니다.")

        if not minimum <= value <= maximum:
            raise ValueError(
                f"{field_name}는 {minimum} 이상 "
                f"{maximum} 이하여야 합니다."
            )


@dataclass(frozen=True)
class RouteGeometryQuery:
    """두 장소 사이의 경로 geometry 조회 조건."""

    origin: GeoCoordinate
    destination: GeoCoordinate
    travel_mode: RouteTravelMode
    departure_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.origin, GeoCoordinate):
            raise TypeError("origin은 GeoCoordinate여야 합니다.")

        if not isinstance(self.destination, GeoCoordinate):
            raise TypeError("destination은 GeoCoordinate여야 합니다.")

        if not isinstance(self.travel_mode, RouteTravelMode):
            raise TypeError(
                "travel_mode는 RouteTravelMode여야 합니다."
            )

        if self.departure_at is not None:
            if not isinstance(self.departure_at, datetime):
                raise TypeError("departure_at은 datetime이어야 합니다.")

            if (
                self.departure_at.tzinfo is None
                or self.departure_at.utcoffset() is None
            ):
                raise ValueError(
                    "departure_at은 timezone-aware datetime이어야 합니다."
                )

        if (
            self.travel_mode is RouteTravelMode.TRANSIT
            and self.departure_at is None
        ):
            raise ValueError(
                "TRANSIT 경로에는 departure_at이 필요합니다."
            )


@dataclass(frozen=True)
class RouteLegGeometry:
    """경로 기반 장소 검색에 전달할 encoded polyline."""

    encoded_polyline: str

    def __post_init__(self) -> None:
        if not isinstance(self.encoded_polyline, str):
            raise TypeError("encoded_polyline은 문자열이어야 합니다.")

        if not self.encoded_polyline.strip():
            raise ValueError(
                "encoded_polyline은 비어 있을 수 없습니다."
            )


@dataclass(frozen=True)
class OptimizedRouteLegGeometryQuery:
    """최적화 방문 순서의 한 구간 geometry 조회 조건."""

    day_index: int
    leg_index: int
    origin_place_id: str
    destination_place_id: str
    geometry_query: RouteGeometryQuery

    def __post_init__(self) -> None:
        _validate_optimized_route_leg(
            day_index=self.day_index,
            leg_index=self.leg_index,
            origin_place_id=self.origin_place_id,
            destination_place_id=self.destination_place_id,
        )
        if not isinstance(self.geometry_query, RouteGeometryQuery):
            raise TypeError("geometry_query는 RouteGeometryQuery여야 합니다.")


@dataclass(frozen=True)
class OptimizedRouteLegGeometry:
    """최적화 경로 구간 식별 정보와 조회된 polyline."""

    day_index: int
    leg_index: int
    origin_place_id: str
    destination_place_id: str
    geometry: RouteLegGeometry

    def __post_init__(self) -> None:
        _validate_optimized_route_leg(
            day_index=self.day_index,
            leg_index=self.leg_index,
            origin_place_id=self.origin_place_id,
            destination_place_id=self.destination_place_id,
        )
        if not isinstance(self.geometry, RouteLegGeometry):
            raise TypeError("geometry는 RouteLegGeometry여야 합니다.")


def _validate_optimized_route_leg(
    *,
    day_index: int,
    leg_index: int,
    origin_place_id: str,
    destination_place_id: str,
) -> None:
    """최적화 경로 구간에 공통으로 필요한 식별 정보를 검증한다."""

    if isinstance(day_index, bool) or not isinstance(day_index, int):
        raise TypeError("day_index는 정수여야 합니다.")
    if day_index < 1:
        raise ValueError("day_index는 1 이상이어야 합니다.")
    if isinstance(leg_index, bool) or not isinstance(leg_index, int):
        raise TypeError("leg_index는 정수여야 합니다.")
    if leg_index < 0:
        raise ValueError("leg_index는 0 이상이어야 합니다.")

    for field_name, place_id in (
        ("origin_place_id", origin_place_id),
        ("destination_place_id", destination_place_id),
    ):
        if not isinstance(place_id, str):
            raise TypeError(f"{field_name}는 문자열이어야 합니다.")
        if not place_id.strip():
            raise ValueError(f"{field_name}는 비어 있을 수 없습니다.")

    if origin_place_id == destination_place_id:
        raise ValueError("출발 장소와 도착 장소는 달라야 합니다.")
