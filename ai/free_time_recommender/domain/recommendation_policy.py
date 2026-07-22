# 빈 시간대 일정 추천에 적용할 순수 도메인 정책
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationPolicy:
    """빈 시간대에 적용할 장소 추천 기준."""

    minimum_stay_minutes: int
    maximum_one_way_travel_minutes: int
    maximum_one_way_distance_meters: int
    candidate_limit: int

    # 초기화 이후 정책 값 검증
    def __post_init__(self) -> None:
        self._validate_positive_integer(
            self.minimum_stay_minutes,
            "minimum_stay_minutes",
        )
        self._validate_non_negative_integer(
            self.maximum_one_way_travel_minutes,
            "maximum_one_way_travel_minutes",
        )
        self._validate_non_negative_integer(
            self.maximum_one_way_distance_meters,
            "maximum_one_way_distance_meters",
        )
        self._validate_positive_integer(
            self.candidate_limit,
            "candidate_limit",
        )
    # 1 이상의 정수 검증
    @staticmethod
    def _validate_positive_integer(
        value: int,
        field_name: str,
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                f"{field_name}는 정수여야 합니다."
            )

        if value <= 0:
            raise ValueError(
                f"{field_name}는 1 이상이어야 합니다."
            )

    # 0 이상의 정수 검증
    @staticmethod
    def _validate_non_negative_integer(
        value: int,
        field_name: str,
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                f"{field_name}는 정수여야 합니다."
            )

        if value < 0:
            raise ValueError(
                f"{field_name}는 0 이상이어야 합니다."
            )
