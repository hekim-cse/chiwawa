# 경로 주변 추천 장소의 카테고리와 후보 모델
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from ai.free_time_recommender.domain.route_geometry import GeoCoordinate


def _validate_non_empty_string(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name}은 문자열이어야 합니다.")
    if not value.strip():
        raise ValueError(f"{field_name}은 비어 있을 수 없습니다.")


class RecommendationCategory(str, Enum):
    """사용자에게 노출할 서버 관리 추천 카테고리."""

    LANDMARK = "LANDMARK"
    CAFE = "CAFE"
    CULTURE = "CULTURE"
    PARK = "PARK"
    RESTAURANT = "RESTAURANT"


@dataclass(frozen=True)
class RecommendationCategoryDefinition:
    """추천 카테고리의 내부 식별자와 화면 표시 정보."""

    category: RecommendationCategory
    display_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.category, RecommendationCategory):
            raise TypeError("category는 RecommendationCategory여야 합니다.")
        _validate_non_empty_string(self.display_name, "display_name")


@dataclass(frozen=True)
class RecommendationCategoryCatalog:
    """검색 순서와 중복 후보의 대표 카테고리를 결정하는 목록."""

    definitions: tuple[RecommendationCategoryDefinition, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.definitions, tuple):
            raise TypeError("definitions는 tuple이어야 합니다.")
        if not self.definitions:
            raise ValueError("definitions는 비어 있을 수 없습니다.")

        categories: set[RecommendationCategory] = set()
        display_names: set[str] = set()
        for definition in self.definitions:
            if not isinstance(definition, RecommendationCategoryDefinition):
                raise TypeError(
                    "definitions의 각 값은 "
                    "RecommendationCategoryDefinition이어야 합니다."
                )
            if definition.category in categories:
                raise ValueError(
                    "definitions에는 중복 카테고리를 사용할 수 없습니다."
                )
            if definition.display_name in display_names:
                raise ValueError(
                    "definitions에는 중복 표시명을 사용할 수 없습니다."
                )
            categories.add(definition.category)
            display_names.add(definition.display_name)


DEFAULT_RECOMMENDATION_CATEGORY_CATALOG = RecommendationCategoryCatalog(
    definitions=(
        RecommendationCategoryDefinition(
            RecommendationCategory.LANDMARK,
            "랜드마크·관광명소",
        ),
        RecommendationCategoryDefinition(RecommendationCategory.CAFE, "카페"),
        RecommendationCategoryDefinition(
            RecommendationCategory.CULTURE,
            "문화·전시 공간",
        ),
        RecommendationCategoryDefinition(
            RecommendationCategory.PARK,
            "공원·정원",
        ),
        RecommendationCategoryDefinition(
            RecommendationCategory.RESTAURANT,
            "음식점",
        ),
    )
)


@dataclass(frozen=True)
class AlongRoutePlaceSearchQuery:
    """한 카테고리의 경로 주변 장소 검색 조건."""

    encoded_polyline: str
    category: RecommendationCategory
    page_size: int
    language_code: str
    region_code: str

    def __post_init__(self) -> None:
        _validate_non_empty_string(self.encoded_polyline, "encoded_polyline")
        if not isinstance(self.category, RecommendationCategory):
            raise TypeError("category는 RecommendationCategory여야 합니다.")
        if isinstance(self.page_size, bool) or not isinstance(self.page_size, int):
            raise TypeError("page_size는 정수여야 합니다.")
        if not 1 <= self.page_size <= 20:
            raise ValueError("page_size는 1 이상 20 이하여야 합니다.")
        _validate_non_empty_string(self.language_code, "language_code")
        _validate_non_empty_string(self.region_code, "region_code")


@dataclass(frozen=True)
class PlaceCandidate:
    """외부 장소 검색 응답을 변환한 내부 추천 후보."""

    place_id: str
    name: str
    coordinate: GeoCoordinate
    category: RecommendationCategory
    formatted_address: str | None = None
    rating: float | None = None
    user_rating_count: int | None = None

    def __post_init__(self) -> None:
        _validate_non_empty_string(self.place_id, "place_id")
        _validate_non_empty_string(self.name, "name")
        if not isinstance(self.coordinate, GeoCoordinate):
            raise TypeError("coordinate는 GeoCoordinate여야 합니다.")
        if not isinstance(self.category, RecommendationCategory):
            raise TypeError("category는 RecommendationCategory여야 합니다.")
        if self.formatted_address is not None:
            _validate_non_empty_string(
                self.formatted_address,
                "formatted_address",
            )
        if self.rating is not None:
            if isinstance(self.rating, bool) or not isinstance(
                self.rating,
                (int, float),
            ):
                raise TypeError("rating은 숫자여야 합니다.")
            if not math.isfinite(self.rating) or not 0 <= self.rating <= 5:
                raise ValueError("rating은 0 이상 5 이하여야 합니다.")
        if self.user_rating_count is not None:
            if isinstance(self.user_rating_count, bool) or not isinstance(
                self.user_rating_count,
                int,
            ):
                raise TypeError("user_rating_count는 정수여야 합니다.")
            if self.user_rating_count < 0:
                raise ValueError("user_rating_count는 0 이상이어야 합니다.")


@dataclass(frozen=True)
class CategoryPlaceCandidates:
    """화면에 표시할 한 카테고리의 중복 제거된 후보 묶음."""

    category: RecommendationCategory
    display_name: str
    candidates: tuple[PlaceCandidate, ...]


@dataclass(frozen=True)
class RouteLegPlaceCandidate:
    """검색된 장소와 해당 장소를 발견한 최적화 경로 구간."""

    candidate: PlaceCandidate
    day_index: int
    leg_index: int
    origin_place_id: str
    destination_place_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, PlaceCandidate):
            raise TypeError("candidate는 PlaceCandidate여야 합니다.")
        for name, value, minimum in (
            ("day_index", self.day_index, 1),
            ("leg_index", self.leg_index, 0),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name}는 정수여야 합니다.")
            if value < minimum:
                raise ValueError(f"{name}는 {minimum} 이상이어야 합니다.")
        _validate_non_empty_string(self.origin_place_id, "origin_place_id")
        _validate_non_empty_string(
            self.destination_place_id,
            "destination_place_id",
        )
        if self.origin_place_id == self.destination_place_id:
            raise ValueError("출발 장소와 도착 장소는 달라야 합니다.")


@dataclass(frozen=True)
class CategoryRouteLegPlaceCandidates:
    """카테고리별 구간 식별 정보가 포함된 장소 후보 묶음."""

    category: RecommendationCategory
    display_name: str
    candidates: tuple[RouteLegPlaceCandidate, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.category, RecommendationCategory):
            raise TypeError("category는 RecommendationCategory여야 합니다.")
        _validate_non_empty_string(self.display_name, "display_name")
        if not isinstance(self.candidates, tuple):
            raise TypeError("candidates는 tuple이어야 합니다.")
        for candidate in self.candidates:
            if not isinstance(candidate, RouteLegPlaceCandidate):
                raise TypeError(
                    "candidates는 RouteLegPlaceCandidate만 포함해야 합니다."
                )
            if candidate.candidate.category is not self.category:
                raise ValueError(
                    "후보 카테고리가 그룹 카테고리와 일치하지 않습니다."
                )
