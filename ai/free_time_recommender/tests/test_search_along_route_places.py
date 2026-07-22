# 카테고리별 경로 주변 장소 후보 검색 Use Case 테스트
from ai.free_time_recommender.application.search_along_route_places import (
    SearchAlongRoutePlaces,
    SearchAlongRoutePlacesRequest,
)
from ai.free_time_recommender.domain.place_candidate import (
    AlongRoutePlaceSearchQuery,
    PlaceCandidate,
    RecommendationCategory,
)
from ai.free_time_recommender.domain.route_geometry import GeoCoordinate


class StubAlongRoutePlaceProvider:
    """카테고리별 고정 후보를 반환하는 테스트 Provider."""

    def __init__(
        self,
        candidates: dict[RecommendationCategory, tuple[PlaceCandidate, ...]],
    ) -> None:
        self.candidates = candidates
        self.queries: list[AlongRoutePlaceSearchQuery] = []

    def search_along_route(
        self,
        query: AlongRoutePlaceSearchQuery,
    ) -> tuple[PlaceCandidate, ...]:
        self.queries.append(query)
        return self.candidates.get(query.category, ())


# 지정 카테고리의 후보 생성 헬퍼
def make_candidate(
    place_id: str,
    category: RecommendationCategory,
) -> PlaceCandidate:
    return PlaceCandidate(
        place_id=place_id,
        name=f"장소 {place_id}",
        coordinate=GeoCoordinate(35.6812, 139.7671),
        category=category,
    )


# 사용자 입력 없이 전체 기본 카테고리를 검색하는 흐름 검증
def test_execute_searches_all_server_managed_categories() -> None:
    provider = StubAlongRoutePlaceProvider({})

    result = SearchAlongRoutePlaces(
        provider=provider,
        candidates_per_category=3,
        language_code="ko",
        region_code="JP",
    ).execute(
        SearchAlongRoutePlacesRequest(
            encoded_polyline="encoded-route",
        )
    )

    assert tuple(query.category for query in provider.queries) == tuple(
        RecommendationCategory
    )
    assert all(query.page_size == 3 for query in provider.queries)
    assert all(query.language_code == "ko" for query in provider.queries)
    assert all(query.region_code == "JP" for query in provider.queries)
    assert tuple(group.category for group in result) == tuple(
        RecommendationCategory
    )


# 같은 장소는 먼저 검색된 카테고리에만 유지되는지 검증
def test_execute_deduplicates_places_by_catalog_priority() -> None:
    provider = StubAlongRoutePlaceProvider(
        {
            RecommendationCategory.LANDMARK: (
                make_candidate("shared", RecommendationCategory.LANDMARK),
                make_candidate("shared", RecommendationCategory.LANDMARK),
            ),
            RecommendationCategory.CAFE: (
                make_candidate("shared", RecommendationCategory.CAFE),
                make_candidate("cafe", RecommendationCategory.CAFE),
            ),
        }
    )

    result = SearchAlongRoutePlaces(
        provider=provider,
        candidates_per_category=3,
        language_code="ko",
        region_code="JP",
    ).execute(
        SearchAlongRoutePlacesRequest(
            encoded_polyline="encoded-route",
        )
    )

    assert tuple(candidate.place_id for candidate in result[0].candidates) == (
        "shared",
    )
    assert tuple(candidate.place_id for candidate in result[1].candidates) == (
        "cafe",
    )


# 서버 설정 후보 수의 Google API 지원 범위 검증
def test_use_case_rejects_invalid_candidates_per_category() -> None:
    provider = StubAlongRoutePlaceProvider({})

    for invalid_value in (0, 21, True):
        try:
            SearchAlongRoutePlaces(
                provider=provider,
                candidates_per_category=invalid_value,
                language_code="ko",
                region_code="JP",
            )
        except (TypeError, ValueError):
            continue
        raise AssertionError("잘못된 후보 수가 허용됐습니다.")


# 한국어 사용자와 일본 여행 지역 외 설정의 조기 거부 검증
def test_use_case_rejects_unsupported_locale_configuration() -> None:
    provider = StubAlongRoutePlaceProvider({})

    for language_code, region_code in (("en", "JP"), ("ko", "KR")):
        try:
            SearchAlongRoutePlaces(
                provider=provider,
                candidates_per_category=3,
                language_code=language_code,
                region_code=region_code,
            )
        except ValueError:
            continue
        raise AssertionError("지원하지 않는 로케일 설정이 허용됐습니다.")
