# 모든 경로 옵션에 초기 추천 흐름을 적용하는 조합 Use Case 테스트
from zoneinfo import ZoneInfo

import pytest

from ai.free_time_recommender.adapters.route_planner_route_option_adapter import (
    RoutePlannerRouteOptionAdapter,
)
from ai.free_time_recommender.adapters.route_planner_timeline_adapter import (
    RoutePlannerTimelineAdapter,
)
from ai.free_time_recommender.application.build_optimized_route_leg_geometries import (
    BuildOptimizedRouteLegGeometries,
)
from ai.free_time_recommender.application.generate_initial_recommendation_groups import (
    GenerateInitialRecommendationGroups,
)
from ai.free_time_recommender.application.generate_route_option_recommendations import (
    GenerateRouteOptionRecommendations,
)
from ai.free_time_recommender.application.search_along_route_places import (
    SearchAlongRoutePlaces,
)
from ai.free_time_recommender.application.search_optimized_route_leg_places import (
    SearchOptimizedRouteLegPlaces,
)
from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)
from ai.free_time_recommender.domain.route_geometry import (
    RouteGeometryQuery,
    RouteLegGeometry,
)
from ai.free_time_recommender.tests.test_optimized_route_leg_geometries import (
    make_route_option,
)
from ai.route_planner.domain.schemas import TravelMode


class StubGeometryProvider:
    def __init__(self) -> None:
        self.queries: list[RouteGeometryQuery] = []

    def get_route_geometry(self, query: RouteGeometryQuery) -> RouteLegGeometry:
        self.queries.append(query)
        return RouteLegGeometry(f"geometry-{len(self.queries)}")


class EmptyPlaceProvider:
    def search_along_route(self, query):
        return ()


class UnusedMetricsProvider:
    def get_candidate_route_metrics(self, query):
        raise AssertionError("빈 후보에서는 이동 지표를 조회하면 안 됩니다.")


def make_option(travel_mode: TravelMode):
    option = make_route_option()
    return option.model_copy(
        update={
            "travel_mode": travel_mode,
            "timeline": option.timeline.model_copy(
                update={
                    "travel_mode": travel_mode,
                    "total_travel_minutes": 120,
                }
            ),
        }
    )


# WALK·DRIVE·TRANSIT을 선택하지 않고 입력 순서대로 모두 반환하는지 검증
def test_execute_returns_recommendations_for_every_route_option() -> None:
    geometry_provider = StubGeometryProvider()
    service = GenerateRouteOptionRecommendations(
        route_option_adapter=RoutePlannerRouteOptionAdapter(),
        timeline_adapter=RoutePlannerTimelineAdapter(),
        geometry_builder=BuildOptimizedRouteLegGeometries(
            provider=geometry_provider
        ),
        place_search=SearchOptimizedRouteLegPlaces(
            search_along_route=SearchAlongRoutePlaces(
                provider=EmptyPlaceProvider(),
                candidates_per_category=2,
                language_code="ko",
                region_code="JP",
            )
        ),
        group_generator=GenerateInitialRecommendationGroups(
            route_metrics_provider=UnusedMetricsProvider(),
            candidates_to_evaluate_per_category=2,
        ),
    )

    result = service.execute(
        route_options=tuple(
            make_option(mode)
            for mode in (
                TravelMode.WALK,
                TravelMode.DRIVE,
                TravelMode.TRANSIT,
            )
        ),
        timezone=ZoneInfo("Asia/Tokyo"),
        policy=RecommendationPolicy(30, 30, 3000, 2),
    )

    assert tuple(item.route_option.travel_mode for item in result) == (
        TravelMode.WALK,
        TravelMode.DRIVE,
        TravelMode.TRANSIT,
    )
    assert all(len(item.route_leg_geometries) == 2 for item in result)
    assert all(item.recommendation_groups == () for item in result)
    assert all(
        query.departure_at.utcoffset().total_seconds() == 9 * 60 * 60
        for query in geometry_provider.queries
    )


# 선택 가능한 경로 옵션이 없으면 정상 빈 결과로 가장하지 않고 요청 거부
def test_execute_rejects_empty_route_options() -> None:
    service = GenerateRouteOptionRecommendations(
        route_option_adapter=RoutePlannerRouteOptionAdapter(),
        timeline_adapter=RoutePlannerTimelineAdapter(),
        geometry_builder=BuildOptimizedRouteLegGeometries(
            provider=StubGeometryProvider()
        ),
        place_search=SearchOptimizedRouteLegPlaces(
            search_along_route=SearchAlongRoutePlaces(
                provider=EmptyPlaceProvider(),
                candidates_per_category=2,
                language_code="ko",
                region_code="JP",
            )
        ),
        group_generator=GenerateInitialRecommendationGroups(
            route_metrics_provider=UnusedMetricsProvider(),
            candidates_to_evaluate_per_category=2,
        ),
    )

    with pytest.raises(ValueError, match="비어 있을 수 없습니다"):
        service.execute(
            route_options=(),
            timezone=ZoneInfo("Asia/Tokyo"),
            policy=RecommendationPolicy(30, 30, 3000, 2),
        )
