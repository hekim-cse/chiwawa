# 추천 후보 경유 전후의 이동시간과 거리 모델
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai.free_time_recommender.domain.route_geometry import RouteTravelMode


def _validate_place_id(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name}는 문자열이어야 합니다.")
    if not value.strip():
        raise ValueError(f"{field_name}는 비어 있을 수 없습니다.")


def _validate_non_negative_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name}는 정수여야 합니다.")
    if value < 0:
        raise ValueError(f"{field_name}는 0 이상이어야 합니다.")


@dataclass(frozen=True)
class CandidateRouteMetricsQuery:
    """후보를 경유하는 두 이동 구간의 계산 조건."""

    previous_place_id: str
    candidate_place_id: str
    next_place_id: str
    previous_departure_at: datetime
    stay_minutes: int
    travel_mode: RouteTravelMode

    def __post_init__(self) -> None:
        _validate_place_id(self.previous_place_id, "previous_place_id")
        _validate_place_id(self.candidate_place_id, "candidate_place_id")
        _validate_place_id(self.next_place_id, "next_place_id")
        if len(
            {
                self.previous_place_id,
                self.candidate_place_id,
                self.next_place_id,
            }
        ) != 3:
            raise ValueError("경로의 세 장소 ID는 서로 달라야 합니다.")
        if not isinstance(self.previous_departure_at, datetime):
            raise TypeError("previous_departure_at은 datetime이어야 합니다.")
        if (
            self.previous_departure_at.tzinfo is None
            or self.previous_departure_at.utcoffset() is None
        ):
            raise ValueError(
                "previous_departure_at은 시간대를 포함해야 합니다."
            )
        if (
            self.previous_departure_at.second != 0
            or self.previous_departure_at.microsecond != 0
        ):
            raise ValueError("previous_departure_at은 분 단위여야 합니다.")
        if isinstance(self.stay_minutes, bool) or not isinstance(
            self.stay_minutes,
            int,
        ):
            raise TypeError("stay_minutes는 정수여야 합니다.")
        if self.stay_minutes <= 0:
            raise ValueError("stay_minutes는 1 이상이어야 합니다.")
        if not isinstance(self.travel_mode, RouteTravelMode):
            raise TypeError("travel_mode는 RouteTravelMode여야 합니다.")


@dataclass(frozen=True)
class RouteLegMetrics:
    """한 이동 구간의 보수적으로 올림한 시간과 실제 거리."""

    travel_minutes: int
    distance_meters: int

    def __post_init__(self) -> None:
        _validate_non_negative_integer(self.travel_minutes, "travel_minutes")
        _validate_non_negative_integer(self.distance_meters, "distance_meters")


@dataclass(frozen=True)
class CandidateRouteMetrics:
    """후보 도착 전후 두 이동 구간의 계산 결과."""

    previous_to_candidate: RouteLegMetrics
    candidate_to_next: RouteLegMetrics
    candidate_arrival_at: datetime
    candidate_departure_at: datetime
    next_arrival_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.previous_to_candidate, RouteLegMetrics):
            raise TypeError(
                "previous_to_candidate는 RouteLegMetrics여야 합니다."
            )
        if not isinstance(self.candidate_to_next, RouteLegMetrics):
            raise TypeError("candidate_to_next는 RouteLegMetrics여야 합니다.")
        for value, field_name in (
            (self.candidate_arrival_at, "candidate_arrival_at"),
            (self.candidate_departure_at, "candidate_departure_at"),
            (self.next_arrival_at, "next_arrival_at"),
        ):
            if not isinstance(value, datetime):
                raise TypeError(f"{field_name}은 datetime이어야 합니다.")
        if self.candidate_departure_at <= self.candidate_arrival_at:
            raise ValueError(
                "candidate_departure_at은 candidate_arrival_at보다 "
                "늦어야 합니다."
            )
        if self.next_arrival_at < self.candidate_departure_at:
            raise ValueError(
                "next_arrival_at은 candidate_departure_at보다 "
                "빠를 수 없습니다."
            )
