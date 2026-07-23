# 경로 최적화와 날짜별 옵션 추천을 연결하는 Application Facade 테스트
from zoneinfo import ZoneInfo

import pytest

from ai.free_time_recommender.application.generate_route_option_recommendations import (
    RouteOptionRecommendationResult,
)
from ai.free_time_recommender.application.plan_trip_with_recommendations import (
    PlanTripWithRecommendations,
    RouteOptionRecommendationStatus,
)
from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)
from ai.free_time_recommender.tests.test_optimized_route_leg_geometries import (
    make_route_option,
)
from ai.route_planner.domain.trip_schemas import (
    DayPlanDTO,
    TripPlanningRequestDTO,
    TripPlanningResponseDTO,
    TripPlanningStatus,
)


class StubTripPlanner:
    def __init__(self, response: TripPlanningResponseDTO) -> None:
        self.response = response
        self.requests: list[TripPlanningRequestDTO] = []

    def plan_trip(self, request: TripPlanningRequestDTO):
        self.requests.append(request)
        return self.response


class StubRecommendationGenerator:
    def __init__(self) -> None:
        self.calls = []

    def execute(self, *, route_options, timezone, policy):
        self.calls.append((route_options, timezone, policy))
        return tuple(
            RouteOptionRecommendationResult(option, (), ())
            for option in route_options
        )


def make_request() -> TripPlanningRequestDTO:
    return TripPlanningRequestDTO.model_construct(
        trip_id="tokyo-trip",
        timezone="Asia/Tokyo",
        days=[],
        pois=[],
    )


def make_response() -> TripPlanningResponseDTO:
    first = make_route_option()
    second = first.model_copy(
        update={
            "day_index": 2,
            "timeline": first.timeline.model_copy(update={"day_index": 2}),
        }
    )
    return TripPlanningResponseDTO.model_construct(
        trip_id="tokyo-trip",
        status=TripPlanningStatus.SUCCESS,
        day_plans=[
            DayPlanDTO.model_construct(day_index=1, route_options=[first]),
            DayPlanDTO.model_construct(day_index=2, route_options=[second]),
        ],
        unassigned_pois=[],
        warnings=[],
    )


# 요청 시간대를 적용해 모든 일자의 경로 옵션을 순서대로 추천 처리
def test_execute_combines_planning_and_day_recommendations() -> None:
    planner = StubTripPlanner(make_response())
    generator = StubRecommendationGenerator()
    policy = RecommendationPolicy(30, 30, 3000, 2)
    request = make_request()

    result = PlanTripWithRecommendations(
        trip_planner=planner,
        recommendation_generator=generator,
    ).execute(request=request, policy=policy)

    assert result.planning.trip_id == "tokyo-trip"
    assert tuple(
        day.day_index for day in result.day_recommendations
    ) == (1, 2)
    assert len(generator.calls) == 2
    assert all(
        isinstance(call[1], ZoneInfo) and call[1].key == "Asia/Tokyo"
        for call in generator.calls
    )
    assert planner.requests == [request]


# Timeline이 없는 이동 방식은 추천 호출에서 제외하고 UNAVAILABLE로 보존
def test_execute_preserves_unavailable_route_option() -> None:
    response = make_response()
    available = response.day_plans[0].route_options[0]
    unavailable = available.model_copy(
        update={
            "travel_mode": "TRANSIT",
            "timeline": None,
            "missing_segments": ["tokyo-station -> tokyo-tower"],
        }
    )
    response.day_plans[0].route_options = [available, unavailable]
    generator = StubRecommendationGenerator()

    result = PlanTripWithRecommendations(
        trip_planner=StubTripPlanner(response),
        recommendation_generator=generator,
    ).execute(
        request=make_request(),
        policy=RecommendationPolicy(30, 30, 3000, 2),
    )

    outcomes = result.day_recommendations[0].route_options
    assert tuple(outcome.status for outcome in outcomes) == (
        RouteOptionRecommendationStatus.SUCCESS,
        RouteOptionRecommendationStatus.UNAVAILABLE,
    )
    assert outcomes[1].recommendation is None
    assert generator.calls[0][0] == (available,)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("route_options", []),
        ("timezone", "Asia/Tokyo"),
        ("policy", object()),
    ],
)
def test_outcome_generator_rejects_invalid_boundary_input(
    field: str,
    invalid_value: object,
) -> None:
    """잘못된 오케스트레이션 입력을 Provider 호출 전에 차단한다."""

    from ai.free_time_recommender.application.plan_trip_with_recommendations import (
        GenerateRouteOptionRecommendationOutcomes,
    )

    arguments = {
        "route_options": (make_route_option(),),
        "timezone": ZoneInfo("Asia/Tokyo"),
        "policy": RecommendationPolicy(30, 30, 3000, 2),
    }
    arguments[field] = invalid_value

    with pytest.raises(TypeError):
        GenerateRouteOptionRecommendationOutcomes(
            StubRecommendationGenerator()
        ).execute(**arguments)
