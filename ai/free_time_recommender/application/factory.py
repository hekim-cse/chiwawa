# Modal에서 Google Provider와 추천 Use Case를 조립하는 Composition Root
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
from ai.free_time_recommender.config import FreeTimeRecommendationSettings
from ai.free_time_recommender.providers.google_along_route_place_provider import (
    GoogleAlongRoutePlaceProvider,
)
from ai.free_time_recommender.providers.google_candidate_route_metrics_provider import (
    GoogleCandidateRouteMetricsProvider,
)
from ai.free_time_recommender.providers.google_routes_geometry_provider import (
    GoogleRoutesGeometryProvider,
)


def build_route_option_recommendation_generator(
    *,
    api_key: str,
    settings: FreeTimeRecommendationSettings,
) -> GenerateRouteOptionRecommendations:
    """검증된 설정으로 옵션별 추천 의존성 그래프를 생성한다."""

    timeout = settings.provider_timeout_seconds
    search = SearchAlongRoutePlaces(
        provider=GoogleAlongRoutePlaceProvider(
            api_key=api_key,
            timeout_seconds=timeout,
        ),
        candidates_per_category=settings.candidates_per_category,
        language_code="ko",
        region_code="JP",
    )
    return GenerateRouteOptionRecommendations(
        route_option_adapter=RoutePlannerRouteOptionAdapter(),
        timeline_adapter=RoutePlannerTimelineAdapter(),
        geometry_builder=BuildOptimizedRouteLegGeometries(
            provider=GoogleRoutesGeometryProvider(
                api_key=api_key,
                timeout_seconds=timeout,
            )
        ),
        place_search=SearchOptimizedRouteLegPlaces(
            search_along_route=search
        ),
        group_generator=GenerateInitialRecommendationGroups(
            route_metrics_provider=GoogleCandidateRouteMetricsProvider(
                api_key=api_key,
                timeout_seconds=timeout,
            ),
            candidates_to_evaluate_per_category=(
                settings.candidates_to_evaluate_per_category
            ),
        ),
    )
