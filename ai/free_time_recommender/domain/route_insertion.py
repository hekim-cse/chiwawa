# 경로 구간별 추천 장소 삽입 영향을 계산하는 순수 도메인
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from ai.free_time_recommender.domain.recommendation_budget import (
    CandidateTravelTimes,
)
from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)


def _validate_integer(
    value: int,
    field_name: str,
    *,
    minimum: int,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name}는 정수여야 합니다.")

    if value < minimum:
        raise ValueError(
            f"{field_name}는 {minimum} 이상이어야 합니다."
        )


def _validate_datetime(
    value: datetime,
    field_name: str,
) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name}은 datetime이어야 합니다.")

    if value.second != 0 or value.microsecond != 0:
        raise ValueError(f"{field_name}은 분 단위로 입력해야 합니다.")


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


@dataclass(frozen=True)
class RouteLegInsertionWindow:
    """추천 후보를 삽입할 기존 경로의 한 이동 구간."""

    day_index: int
    leg_index: int
    previous_place_id: str
    next_place_id: str
    previous_departure_at: datetime
    next_arrival_at: datetime
    original_travel_minutes: int
    original_timeline_end_at: datetime
    planned_end_at: datetime

    def __post_init__(self) -> None:
        _validate_integer(self.day_index, "day_index", minimum=1)
        _validate_integer(self.leg_index, "leg_index", minimum=0)
        self._validate_place_id(
            self.previous_place_id,
            "previous_place_id",
        )
        self._validate_place_id(
            self.next_place_id,
            "next_place_id",
        )

        datetime_fields = (
            (self.previous_departure_at, "previous_departure_at"),
            (self.next_arrival_at, "next_arrival_at"),
            (
                self.original_timeline_end_at,
                "original_timeline_end_at",
            ),
            (self.planned_end_at, "planned_end_at"),
        )
        for value, field_name in datetime_fields:
            _validate_datetime(value, field_name)

        timezone_awareness = {
            _is_timezone_aware(value)
            for value, _ in datetime_fields
        }
        if len(timezone_awareness) != 1:
            raise ValueError(
                "경로 구간의 모든 시각은 동일한 시간대 형식을 "
                "사용해야 합니다."
            )

        if self.next_arrival_at < self.previous_departure_at:
            raise ValueError(
                "next_arrival_at은 previous_departure_at보다 "
                "빠를 수 없습니다."
            )

        if self.original_timeline_end_at < self.next_arrival_at:
            raise ValueError(
                "original_timeline_end_at은 next_arrival_at보다 "
                "빠를 수 없습니다."
            )

        _validate_integer(
            self.original_travel_minutes,
            "original_travel_minutes",
            minimum=0,
        )
        expected_travel_minutes = int(
            (
                self.next_arrival_at
                - self.previous_departure_at
            ).total_seconds()
            // 60
        )
        if self.original_travel_minutes != expected_travel_minutes:
            raise ValueError(
                "original_travel_minutes는 기존 이동 구간의 "
                "실제 시간과 일치해야 합니다."
            )

    @staticmethod
    def _validate_place_id(value: str, field_name: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name}는 문자열이어야 합니다.")

        if not value.strip():
            raise ValueError(f"{field_name}는 비어 있을 수 없습니다.")


@dataclass(frozen=True)
class CandidateInsertionSchedule:
    """후보 장소를 경유할 때 적용할 이동시간과 체류시간."""

    travel_times: CandidateTravelTimes
    previous_to_candidate_distance_meters: int
    candidate_to_next_distance_meters: int
    stay_minutes: int

    def __post_init__(self) -> None:
        if not isinstance(self.travel_times, CandidateTravelTimes):
            raise TypeError(
                "travel_times는 CandidateTravelTimes여야 합니다."
            )

        _validate_integer(
            self.previous_to_candidate_distance_meters,
            "previous_to_candidate_distance_meters",
            minimum=0,
        )
        _validate_integer(
            self.candidate_to_next_distance_meters,
            "candidate_to_next_distance_meters",
            minimum=0,
        )

        _validate_integer(
            self.stay_minutes,
            "stay_minutes",
            minimum=1,
        )


class RouteInsertionRejectionReason(str, Enum):
    """경로 구간에 추천 후보를 삽입할 수 없는 사유."""

    STAY_DURATION_BELOW_MINIMUM = "STAY_DURATION_BELOW_MINIMUM"
    PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED = (
        "PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED"
    )
    CANDIDATE_TO_NEXT_LIMIT_EXCEEDED = (
        "CANDIDATE_TO_NEXT_LIMIT_EXCEEDED"
    )
    PREVIOUS_TO_CANDIDATE_DISTANCE_LIMIT_EXCEEDED = (
        "PREVIOUS_TO_CANDIDATE_DISTANCE_LIMIT_EXCEEDED"
    )
    CANDIDATE_TO_NEXT_DISTANCE_LIMIT_EXCEEDED = (
        "CANDIDATE_TO_NEXT_DISTANCE_LIMIT_EXCEEDED"
    )
    PLANNED_END_EXCEEDED = "PLANNED_END_EXCEEDED"


@dataclass(frozen=True)
class RouteLegInsertionImpact:
    """추천 후보 삽입 전후의 일정 시간 변화와 실패 사유."""

    replacement_travel_minutes: int
    replacement_total_minutes: int
    additional_minutes: int
    updated_next_arrival_at: datetime
    updated_timeline_end_at: datetime
    remaining_minutes: int
    rejection_reasons: tuple[RouteInsertionRejectionReason, ...]

    @property
    def is_insertable(self) -> bool:
        return not self.rejection_reasons


class EvaluateRouteLegInsertionImpact:
    """추천 후보를 경유할 때 전체 일정에 추가되는 시간을 평가."""

    def evaluate(
        self,
        window: RouteLegInsertionWindow,
        policy: RecommendationPolicy,
        candidate_schedule: CandidateInsertionSchedule,
    ) -> RouteLegInsertionImpact:
        travel_times = candidate_schedule.travel_times
        replacement_travel_minutes = (
            travel_times.previous_to_candidate_minutes
            + travel_times.candidate_to_next_minutes
        )
        replacement_total_minutes = (
            replacement_travel_minutes
            + candidate_schedule.stay_minutes
        )
        additional_minutes = (
            replacement_total_minutes
            - window.original_travel_minutes
        )
        updated_next_arrival_at = (
            window.next_arrival_at
            + timedelta(minutes=additional_minutes)
        )
        updated_timeline_end_at = (
            window.original_timeline_end_at
            + timedelta(minutes=additional_minutes)
        )
        remaining_minutes = int(
            (
                window.planned_end_at
                - updated_timeline_end_at
            ).total_seconds()
            // 60
        )

        reasons: list[RouteInsertionRejectionReason] = []
        if candidate_schedule.stay_minutes < policy.minimum_stay_minutes:
            reasons.append(
                RouteInsertionRejectionReason
                .STAY_DURATION_BELOW_MINIMUM
            )

        if (
            travel_times.previous_to_candidate_minutes
            > policy.maximum_one_way_travel_minutes
        ):
            reasons.append(
                RouteInsertionRejectionReason
                .PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED
            )

        if (
            travel_times.candidate_to_next_minutes
            > policy.maximum_one_way_travel_minutes
        ):
            reasons.append(
                RouteInsertionRejectionReason
                .CANDIDATE_TO_NEXT_LIMIT_EXCEEDED
            )

        if (
            candidate_schedule.previous_to_candidate_distance_meters
            > policy.maximum_one_way_distance_meters
        ):
            reasons.append(
                RouteInsertionRejectionReason
                .PREVIOUS_TO_CANDIDATE_DISTANCE_LIMIT_EXCEEDED
            )

        if (
            candidate_schedule.candidate_to_next_distance_meters
            > policy.maximum_one_way_distance_meters
        ):
            reasons.append(
                RouteInsertionRejectionReason
                .CANDIDATE_TO_NEXT_DISTANCE_LIMIT_EXCEEDED
            )

        if updated_timeline_end_at > window.planned_end_at:
            reasons.append(
                RouteInsertionRejectionReason.PLANNED_END_EXCEEDED
            )

        return RouteLegInsertionImpact(
            replacement_travel_minutes=replacement_travel_minutes,
            replacement_total_minutes=replacement_total_minutes,
            additional_minutes=additional_minutes,
            updated_next_arrival_at=updated_next_arrival_at,
            updated_timeline_end_at=updated_timeline_end_at,
            remaining_minutes=remaining_minutes,
            rejection_reasons=tuple(reasons),
        )
