# Route Planner의 모든 경로 옵션에 초기 추천 그룹을 결합하는 Use Case
from dataclasses import dataclass
from zoneinfo import ZoneInfo

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
    GenerateInitialRecommendationGroupsRequest,
    InitialRecommendationGroup,
)
from ai.free_time_recommender.application.search_optimized_route_leg_places import (
    SearchOptimizedRouteLegPlaces,
)
from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)
from ai.free_time_recommender.domain.route_geometry import (
    OptimizedRouteLegGeometry,
)
from ai.route_planner.domain.trip_schemas import RouteOptionDTO


@dataclass(frozen=True)
class RouteOptionRecommendationResult:
    """사용자가 선택할 한 경로 옵션과 해당 옵션의 추천 결과."""

    route_option: RouteOptionDTO
    route_leg_geometries: tuple[OptimizedRouteLegGeometry, ...]
    recommendation_groups: tuple[InitialRecommendationGroup, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.route_option, RouteOptionDTO):
            raise TypeError("route_option은 RouteOptionDTO여야 합니다.")
        if not isinstance(self.route_leg_geometries, tuple):
            raise TypeError("route_leg_geometries는 tuple이어야 합니다.")
        if not isinstance(self.recommendation_groups, tuple):
            raise TypeError("recommendation_groups는 tuple이어야 합니다.")


class GenerateRouteOptionRecommendations:
    """경로 옵션을 선택하지 않고 입력 순서대로 모두 추천 처리한다."""

    def __init__(
        self,
        *,
        route_option_adapter: RoutePlannerRouteOptionAdapter,
        timeline_adapter: RoutePlannerTimelineAdapter,
        geometry_builder: BuildOptimizedRouteLegGeometries,
        place_search: SearchOptimizedRouteLegPlaces,
        group_generator: GenerateInitialRecommendationGroups,
    ) -> None:
        self._route_option_adapter = route_option_adapter
        self._timeline_adapter = timeline_adapter
        self._geometry_builder = geometry_builder
        self._place_search = place_search
        self._group_generator = group_generator

    def execute(
        self,
        *,
        route_options: tuple[RouteOptionDTO, ...],
        timezone: ZoneInfo,
        policy: RecommendationPolicy,
    ) -> tuple[RouteOptionRecommendationResult, ...]:
        if not isinstance(route_options, tuple):
            raise TypeError("route_options는 tuple이어야 합니다.")
        if not route_options:
            raise ValueError("route_options는 비어 있을 수 없습니다.")
        if not isinstance(timezone, ZoneInfo):
            raise TypeError("timezone은 ZoneInfo여야 합니다.")
        if not isinstance(policy, RecommendationPolicy):
            raise TypeError("policy는 RecommendationPolicy여야 합니다.")

        results: list[RouteOptionRecommendationResult] = []
        for route_option in route_options:
            if not isinstance(route_option, RouteOptionDTO):
                raise TypeError("route_options는 RouteOptionDTO만 포함해야 합니다.")
            if route_option.timeline is None:
                raise ValueError("추천을 생성할 경로 옵션에는 Timeline이 필요합니다.")

            queries = self._route_option_adapter.to_geometry_queries(
                route_option,
                timezone,
            )
            geometries = self._geometry_builder.execute(queries)
            candidate_groups = self._place_search.execute(geometries)
            windows = (
                self._timeline_adapter
                .to_timezone_aware_route_leg_insertion_windows(
                    route_option.timeline,
                    timezone,
                )
            )
            groups = self._group_generator.execute(
                GenerateInitialRecommendationGroupsRequest(
                    candidate_groups=candidate_groups,
                    insertion_windows=windows,
                    travel_mode=queries[0].geometry_query.travel_mode,
                    policy=policy,
                )
            )
            results.append(
                RouteOptionRecommendationResult(
                    route_option=route_option,
                    route_leg_geometries=geometries,
                    recommendation_groups=groups,
                )
            )
        return tuple(results)
