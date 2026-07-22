# 경로 최적화와 날짜별 경로 옵션 추천을 조합하는 Application Facade
from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ai.free_time_recommender.application.generate_route_option_recommendations import (
    RouteOptionRecommendationResult,
)
from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)
from ai.route_planner.domain.trip_schemas import (
    RouteOptionDTO,
    TripPlanningRequestDTO,
    TripPlanningResponseDTO,
)


class TripPlanner(Protocol):
    def plan_trip(
        self,
        request: TripPlanningRequestDTO,
    ) -> TripPlanningResponseDTO:
        ...


class RouteOptionRecommendationGenerator(Protocol):
    def execute(
        self,
        *,
        route_options: tuple[RouteOptionDTO, ...],
        timezone: ZoneInfo,
        policy: RecommendationPolicy,
    ) -> tuple[RouteOptionRecommendationResult, ...]:
        ...


class RouteOptionRecommendationStatus(str, Enum):
    """경로 옵션별 추천 생성 상태."""

    SUCCESS = "SUCCESS"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class RouteOptionRecommendationOutcome:
    """사용 불가 이동 방식까지 보존하는 옵션별 추천 결과."""

    route_option: RouteOptionDTO
    status: RouteOptionRecommendationStatus
    recommendation: RouteOptionRecommendationResult | None

    def __post_init__(self) -> None:
        if self.status is RouteOptionRecommendationStatus.SUCCESS:
            if self.recommendation is None:
                raise ValueError("SUCCESS 결과에는 추천 결과가 필요합니다.")
            if self.recommendation.route_option != self.route_option:
                raise ValueError("추천 결과의 경로 옵션이 원본과 다릅니다.")
        elif self.recommendation is not None:
            raise ValueError("UNAVAILABLE 결과에는 추천 결과가 없어야 합니다.")


class GenerateRouteOptionRecommendationOutcomes:
    """사용 불가 옵션을 보존하며 추천 가능한 옵션만 실행한다."""

    def __init__(self, generator: RouteOptionRecommendationGenerator) -> None:
        self._generator = generator

    def execute(self, *, route_options, timezone, policy):
        available = tuple(
            option for option in route_options if option.timeline is not None
        )
        recommendations = (
            self._generator.execute(
                route_options=available,
                timezone=timezone,
                policy=policy,
            )
            if available
            else ()
        )
        if len(recommendations) != len(available):
            raise ValueError("경로 옵션 수와 추천 결과 수가 일치하지 않습니다.")
        iterator = iter(recommendations)
        outcomes = []
        for option in route_options:
            recommendation = next(iterator) if option.timeline is not None else None
            outcomes.append(
                RouteOptionRecommendationOutcome(
                    route_option=option,
                    status=(
                        RouteOptionRecommendationStatus.SUCCESS
                        if recommendation is not None
                        else RouteOptionRecommendationStatus.UNAVAILABLE
                    ),
                    recommendation=recommendation,
                )
            )
        return tuple(outcomes)


@dataclass(frozen=True)
class DayRouteOptionRecommendations:
    """한 여행 일자의 모든 경로 옵션 추천 결과."""

    day_index: int
    route_options: tuple[RouteOptionRecommendationOutcome, ...]


@dataclass(frozen=True)
class TripPlanWithRecommendations:
    """경로 최적화 원본 응답과 날짜별 추천 조합 결과."""

    planning: TripPlanningResponseDTO
    day_recommendations: tuple[DayRouteOptionRecommendations, ...]


class PlanTripWithRecommendations:
    """요청 한 번으로 경로 최적화 후 모든 옵션 추천을 생성한다."""

    def __init__(
        self,
        *,
        trip_planner: TripPlanner,
        recommendation_generator: RouteOptionRecommendationGenerator,
    ) -> None:
        self._trip_planner = trip_planner
        self._outcome_generator = GenerateRouteOptionRecommendationOutcomes(
            recommendation_generator
        )

    def execute(
        self,
        *,
        request: TripPlanningRequestDTO,
        policy: RecommendationPolicy,
    ) -> TripPlanWithRecommendations:
        if not isinstance(request, TripPlanningRequestDTO):
            raise TypeError("request는 TripPlanningRequestDTO여야 합니다.")
        if not isinstance(policy, RecommendationPolicy):
            raise TypeError("policy는 RecommendationPolicy여야 합니다.")
        try:
            timezone = ZoneInfo(request.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("지원하지 않는 IANA 여행 시간대입니다.") from error

        planning = self._trip_planner.plan_trip(request)
        if not isinstance(planning, TripPlanningResponseDTO):
            raise TypeError(
                "Trip Planner 결과는 TripPlanningResponseDTO여야 합니다."
            )
        if planning.trip_id != request.trip_id:
            raise ValueError("Trip Planner 결과의 trip_id가 요청과 다릅니다.")
        if not planning.day_plans:
            raise ValueError("Trip Planner 결과에 여행 일자가 없습니다.")

        results: list[DayRouteOptionRecommendations] = []
        seen_day_indexes: set[int] = set()
        for day_plan in planning.day_plans:
            if day_plan.day_index in seen_day_indexes:
                raise ValueError("Trip Planner 결과의 day_index가 중복됩니다.")
            seen_day_indexes.add(day_plan.day_index)
            route_options = tuple(day_plan.route_options)
            if not route_options:
                raise ValueError(
                    f"{day_plan.day_index}일차에 경로 옵션이 없습니다."
                )
            if any(
                option.day_index != day_plan.day_index
                for option in route_options
            ):
                raise ValueError(
                    "DayPlan과 경로 옵션의 day_index가 일치하지 않습니다."
                )
            outcomes = self._outcome_generator.execute(
                route_options=route_options,
                timezone=timezone,
                policy=policy,
            )
            results.append(
                DayRouteOptionRecommendations(
                    day_index=day_plan.day_index,
                    route_options=outcomes,
                )
            )

        return TripPlanWithRecommendations(
            planning=planning,
            day_recommendations=tuple(results),
        )
