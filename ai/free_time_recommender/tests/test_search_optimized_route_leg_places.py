# 최적화 경로 구간별 장소 검색 결과 통합 테스트
from ai.free_time_recommender.application.search_along_route_places import (
    SearchAlongRoutePlacesRequest,
)
from ai.free_time_recommender.application.search_optimized_route_leg_places import (
    SearchOptimizedRouteLegPlaces,
)
from ai.free_time_recommender.domain.place_candidate import (
    CategoryPlaceCandidates,
    PlaceCandidate,
    RecommendationCategory,
)
from ai.free_time_recommender.domain.route_geometry import (
    GeoCoordinate,
    OptimizedRouteLegGeometry,
    RouteLegGeometry,
)


class StubSearchAlongRoutePlaces:
    """polyline별 카테고리 검색 결과를 반환하는 테스트 검색기."""

    def execute(self, request: SearchAlongRoutePlacesRequest):
        place_id = "shared" if request.encoded_polyline == "leg-0" else "leg-1"
        candidate = PlaceCandidate(
            place_id=place_id,
            name="도쿄 추천 장소",
            coordinate=GeoCoordinate(35.68, 139.76),
            category=RecommendationCategory.LANDMARK,
        )
        return (
            CategoryPlaceCandidates(
                RecommendationCategory.LANDMARK,
                "랜드마크·관광명소",
                (candidate,),
            ),
        )


def make_geometry(leg_index: int) -> OptimizedRouteLegGeometry:
    return OptimizedRouteLegGeometry(
        day_index=1,
        leg_index=leg_index,
        origin_place_id=f"place-{leg_index}",
        destination_place_id=f"place-{leg_index + 1}",
        geometry=RouteLegGeometry(f"leg-{leg_index}"),
    )


# 후보에 최초로 검색된 경로 구간 식별 정보가 보존되는지 검증
def test_execute_connects_candidates_to_source_route_leg() -> None:
    result = SearchOptimizedRouteLegPlaces(
        search_along_route=StubSearchAlongRoutePlaces(),
    ).execute((make_geometry(0), make_geometry(1)))

    assert tuple(
        candidate.leg_index for candidate in result[0].candidates
    ) == (0, 1)
    assert result[0].candidates[0].origin_place_id == "place-0"
    assert result[0].candidates[1].destination_place_id == "place-2"
