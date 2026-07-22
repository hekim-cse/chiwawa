# 경로 주변 추천 장소 도메인 모델과 카탈로그 테스트
import pytest

from ai.free_time_recommender.domain.place_candidate import (
    AlongRoutePlaceSearchQuery,
    DEFAULT_RECOMMENDATION_CATEGORY_CATALOG,
    PlaceCandidate,
    RecommendationCategory,
    RecommendationCategoryCatalog,
    RecommendationCategoryDefinition,
)
from ai.free_time_recommender.domain.route_geometry import GeoCoordinate


# 기본 카탈로그의 노출 순서와 표시명 검증
def test_default_category_catalog_has_expected_categories() -> None:
    assert tuple(
        (definition.category, definition.display_name)
        for definition in DEFAULT_RECOMMENDATION_CATEGORY_CATALOG.definitions
    ) == (
        (RecommendationCategory.LANDMARK, "랜드마크·관광명소"),
        (RecommendationCategory.CAFE, "카페"),
        (RecommendationCategory.CULTURE, "문화·전시 공간"),
        (RecommendationCategory.PARK, "공원·정원"),
        (RecommendationCategory.RESTAURANT, "음식점"),
    )


# 카탈로그의 중복 카테고리와 중복 표시명 거부 검증
@pytest.mark.parametrize(
    "definitions",
    [
        (
            RecommendationCategoryDefinition(
                RecommendationCategory.CAFE,
                "카페",
            ),
            RecommendationCategoryDefinition(
                RecommendationCategory.CAFE,
                "커피",
            ),
        ),
        (
            RecommendationCategoryDefinition(
                RecommendationCategory.CAFE,
                "추천",
            ),
            RecommendationCategoryDefinition(
                RecommendationCategory.PARK,
                "추천",
            ),
        ),
    ],
)
def test_category_catalog_rejects_duplicates(
    definitions: tuple[RecommendationCategoryDefinition, ...],
) -> None:
    with pytest.raises(ValueError):
        RecommendationCategoryCatalog(definitions)


# 경로 검색 조건의 잘못된 페이지 크기 거부 검증
@pytest.mark.parametrize("page_size", [0, 21, True, 1.5])
def test_search_query_rejects_invalid_page_size(page_size: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        AlongRoutePlaceSearchQuery(
            encoded_polyline="encoded-route",
            category=RecommendationCategory.CAFE,
            page_size=page_size,  # type: ignore[arg-type]
            language_code="ko",
            region_code="JP",
        )


# 후보 장소의 평점과 리뷰 수 경계값 검증
@pytest.mark.parametrize(
    ("rating", "user_rating_count"),
    [(-0.1, 0), (5.1, 0), (float("nan"), 0), (4.5, -1)],
)
def test_place_candidate_rejects_invalid_rating_data(
    rating: float,
    user_rating_count: int,
) -> None:
    with pytest.raises(ValueError):
        PlaceCandidate(
            place_id="place-1",
            name="장소",
            coordinate=GeoCoordinate(35.6812, 139.7671),
            category=RecommendationCategory.CAFE,
            rating=rating,
            user_rating_count=user_rating_count,
        )
