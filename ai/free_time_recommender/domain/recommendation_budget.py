# 추천 장소 삽입에 사용할 순수 시간 예산 도메인
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)


def _validate_non_negative_integer(
    value: int,
    field_name: str,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name}는 정수여야 합니다.")

    if value < 0:
        raise ValueError(f"{field_name}는 0 이상이어야 합니다.")


@dataclass(frozen=True)
class RecommendationTimeWindow:
    """추천 장소를 마지막 방문지와 최종 도착지 사이에 삽입할 시간 범위."""

    day_index: int
    start_at: datetime
    end_at: datetime
    available_minutes: int
    previous_place_id: str
    next_place_id: str

    def __post_init__(self) -> None:
        if isinstance(self.day_index, bool) or not isinstance(
            self.day_index,
            int,
        ):
            raise TypeError("day_index는 정수여야 합니다.")

        if self.day_index < 1:
            raise ValueError("day_index는 1 이상이어야 합니다.")

        if not isinstance(self.start_at, datetime):
            raise TypeError("start_at은 datetime이어야 합니다.")

        if not isinstance(self.end_at, datetime):
            raise TypeError("end_at은 datetime이어야 합니다.")

        for value, field_name in (
            (self.start_at, "start_at"),
            (self.end_at, "end_at"),
        ):
            if value.second != 0 or value.microsecond != 0:
                raise ValueError(
                    f"{field_name}은 분 단위로 입력해야 합니다."
                )

        start_is_aware = (
            self.start_at.tzinfo is not None
            and self.start_at.utcoffset() is not None
        )
        end_is_aware = (
            self.end_at.tzinfo is not None
            and self.end_at.utcoffset() is not None
        )

        if start_is_aware != end_is_aware:
            raise ValueError(
                "start_at과 end_at은 동일한 시간대 형식을 사용해야 합니다."
            )

        if self.end_at <= self.start_at:
            raise ValueError("end_at은 start_at보다 늦어야 합니다.")

        _validate_non_negative_integer(
            self.available_minutes,
            "available_minutes",
        )

        expected_minutes = int(
            (self.end_at - self.start_at).total_seconds() // 60
        )
        if self.available_minutes != expected_minutes:
            raise ValueError(
                "available_minutes는 실제 시간 범위와 일치해야 합니다."
            )

        self._validate_place_id(
            self.previous_place_id,
            "previous_place_id",
        )
        self._validate_place_id(
            self.next_place_id,
            "next_place_id",
        )

    @staticmethod
    def _validate_place_id(value: str, field_name: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name}는 문자열이어야 합니다.")

        if not value.strip():
            raise ValueError(f"{field_name}는 비어 있을 수 없습니다.")


@dataclass(frozen=True)
class CandidateTravelTimes:
    """추천 후보를 경유할 때 필요한 양쪽 편도 이동시간."""

    previous_to_candidate_minutes: int
    candidate_to_next_minutes: int

    def __post_init__(self) -> None:
        _validate_non_negative_integer(
            self.previous_to_candidate_minutes,
            "previous_to_candidate_minutes",
        )
        _validate_non_negative_integer(
            self.candidate_to_next_minutes,
            "candidate_to_next_minutes",
        )


class RecommendationRejectionReason(str, Enum):
    """추천 후보가 시간 정책을 충족하지 못한 사유."""

    PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED = (
        "PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED"
    )
    CANDIDATE_TO_NEXT_LIMIT_EXCEEDED = (
        "CANDIDATE_TO_NEXT_LIMIT_EXCEEDED"
    )
    INSUFFICIENT_TOTAL_TIME = "INSUFFICIENT_TOTAL_TIME"


@dataclass(frozen=True)
class RecommendationFeasibility:
    """추천 가능 여부와 시간 예산 계산 결과."""

    required_minutes: int
    remaining_minutes: int
    rejection_reasons: tuple[RecommendationRejectionReason, ...]

    @property
    def is_recommendable(self) -> bool:
        return not self.rejection_reasons


class EvaluateRecommendationFeasibility:
    """후보 장소의 이동·체류 시간이 추천 정책을 만족하는지 평가."""

    def evaluate(
        self,
        window: RecommendationTimeWindow,
        policy: RecommendationPolicy,
        travel_times: CandidateTravelTimes,
    ) -> RecommendationFeasibility:
        required_minutes = (
            travel_times.previous_to_candidate_minutes
            + policy.minimum_stay_minutes
            + travel_times.candidate_to_next_minutes
        )
        remaining_minutes = window.available_minutes - required_minutes

        reasons: list[RecommendationRejectionReason] = []
        if (
            travel_times.previous_to_candidate_minutes
            > policy.maximum_one_way_travel_minutes
        ):
            reasons.append(
                RecommendationRejectionReason
                .PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED
            )

        if (
            travel_times.candidate_to_next_minutes
            > policy.maximum_one_way_travel_minutes
        ):
            reasons.append(
                RecommendationRejectionReason
                .CANDIDATE_TO_NEXT_LIMIT_EXCEEDED
            )

        if remaining_minutes < 0:
            reasons.append(
                RecommendationRejectionReason.INSUFFICIENT_TOTAL_TIME
            )

        return RecommendationFeasibility(
            required_minutes=required_minutes,
            remaining_minutes=remaining_minutes,
            rejection_reasons=tuple(reasons),
        )
