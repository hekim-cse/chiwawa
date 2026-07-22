# 빈 시간대 일정 추천에 적용할 순수 도메인 정책
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationPolicy:
    """빈 시간대에 적용할 장소 추천 기준."""

    minimum_stay_minutes: int
    maximum_one_way_travel_minutes: int
    maximum_distance_meters: int
    candidate_limit: int
    allowed_categories: tuple[str, ...]

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
            self.maximum_distance_meters,
            "maximum_distance_meters",
        )
        self._validate_positive_integer(
            self.candidate_limit,
            "candidate_limit",
        )
        self._validate_allowed_categories()

    # 허용 카테고리 검증
    def _validate_allowed_categories(self) -> None:
        if not isinstance(self.allowed_categories, tuple):
            raise TypeError(
                "allowed_categories는 tuple이어야 합니다."
            )

        if not self.allowed_categories:
            raise ValueError(
                "allowed_categories는 1개 이상의 카테고리를 포함해야 합니다."
            )

        seen_categories: set[str] = set()

        for category in self.allowed_categories:
            if not isinstance(category, str):
                raise TypeError(
                    "allowed_categories의 각 값은 문자열이어야 합니다."
                )

            if not category.strip():
                raise ValueError(
                    "allowed_categories에는 빈 문자열을 사용할 수 없습니다."
                )

            if category in seen_categories:
                raise ValueError(
                    "allowed_categories에는 중복 값을 사용할 수 없습니다."
                )

            seen_categories.add(category)

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
