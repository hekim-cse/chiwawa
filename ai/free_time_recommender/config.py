# Modal 환경변수에서 빈 시간대 추천 운영 설정을 읽는 설정 객체
from dataclasses import dataclass
from os import environ
from typing import Mapping

from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)


@dataclass(frozen=True)
class FreeTimeRecommendationSettings:
    """외부 호출량과 추천 허용 범위를 결정하는 운영 설정."""

    minimum_stay_minutes: int
    maximum_one_way_travel_minutes: int
    maximum_one_way_distance_meters: int
    candidates_per_category: int
    candidates_to_evaluate_per_category: int
    provider_timeout_seconds: int

    @classmethod
    def from_environment(
        cls,
        values: Mapping[str, str] = environ,
    ) -> "FreeTimeRecommendationSettings":
        return cls(
            minimum_stay_minutes=cls._positive_integer(
                values, "FREE_TIME_MINIMUM_STAY_MINUTES"
            ),
            maximum_one_way_travel_minutes=cls._non_negative_integer(
                values, "FREE_TIME_MAXIMUM_ONE_WAY_TRAVEL_MINUTES"
            ),
            maximum_one_way_distance_meters=cls._non_negative_integer(
                values, "FREE_TIME_MAXIMUM_ONE_WAY_DISTANCE_METERS"
            ),
            candidates_per_category=cls._bounded_integer(
                values,
                "FREE_TIME_CANDIDATES_PER_CATEGORY",
                minimum=1,
                maximum=20,
            ),
            candidates_to_evaluate_per_category=cls._positive_integer(
                values, "FREE_TIME_CANDIDATES_TO_EVALUATE_PER_CATEGORY"
            ),
            provider_timeout_seconds=cls._positive_integer(
                values, "FREE_TIME_PROVIDER_TIMEOUT_SECONDS"
            ),
        )

    @property
    def policy(self) -> RecommendationPolicy:
        return RecommendationPolicy(
            minimum_stay_minutes=self.minimum_stay_minutes,
            maximum_one_way_travel_minutes=(
                self.maximum_one_way_travel_minutes
            ),
            maximum_one_way_distance_meters=(
                self.maximum_one_way_distance_meters
            ),
            candidate_limit=self.candidates_to_evaluate_per_category,
        )

    @staticmethod
    def _read(values: Mapping[str, str], name: str) -> str:
        value = values.get(name)
        if value is None or not value.strip():
            raise ValueError(f"필수 환경변수 {name}가 설정되지 않았습니다.")
        return value

    @classmethod
    def _positive_integer(cls, values: Mapping[str, str], name: str) -> int:
        return cls._bounded_integer(values, name, minimum=1)

    @classmethod
    def _non_negative_integer(
        cls,
        values: Mapping[str, str],
        name: str,
    ) -> int:
        return cls._bounded_integer(values, name, minimum=0)

    @classmethod
    def _bounded_integer(
        cls,
        values: Mapping[str, str],
        name: str,
        *,
        minimum: int,
        maximum: int | None = None,
    ) -> int:
        text = cls._read(values, name)
        try:
            value = int(text)
        except ValueError as error:
            raise ValueError(f"환경변수 {name}는 정수여야 합니다.") from error
        if value < minimum or (maximum is not None and value > maximum):
            maximum_text = f" {maximum} 이하" if maximum is not None else ""
            raise ValueError(
                f"환경변수 {name}는 {minimum} 이상{maximum_text}이어야 합니다."
            )
        return value
