# Modal 통합 일정 최적화·추천 응답 계약과
# Application 결과 변환 Adapter
from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai.free_time_recommender.application.plan_trip_with_recommendations import (
    RouteOptionRecommendationOutcome,
    RouteOptionRecommendationStatus,
    TripPlanWithRecommendations,
)
from ai.free_time_recommender.domain.place_candidate import (
    RecommendationCategory,
)
from ai.free_time_recommender.domain.route_insertion import (
    RouteInsertionRejectionReason,
)
from ai.route_planner.domain.trip_schemas import (
    DayPlanDTO,
    RouteOptionDTO,
    TripPlanningStatus,
    UnassignedPoiDTO,
)


class ModalResponseDTO(BaseModel):
    """Modal 외부 응답에 공통으로 적용할 엄격한 계약 설정."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )


class GeoCoordinateResponseDTO(ModalResponseDTO):
    """추천 장소의 위도·경도 응답."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class PlaceCandidateResponseDTO(ModalResponseDTO):
    """경로 주변에서 검색한 추천 장소 응답."""

    place_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    coordinate: GeoCoordinateResponseDTO
    category: RecommendationCategory
    formatted_address: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    user_rating_count: int | None = Field(default=None, ge=0)


class RouteLegInsertionWindowResponseDTO(ModalResponseDTO):
    """추천 장소가 삽입될 기존 일정 구간 응답."""

    day_index: int = Field(ge=1)
    leg_index: int = Field(ge=0)
    previous_place_id: str = Field(min_length=1)
    next_place_id: str = Field(min_length=1)
    previous_departure_at: datetime
    next_arrival_at: datetime
    original_travel_minutes: int = Field(ge=0)
    original_timeline_end_at: datetime
    planned_end_at: datetime


class RouteLegMetricsResponseDTO(ModalResponseDTO):
    """추천 장소 전후 한쪽 이동 지표 응답."""

    travel_minutes: int = Field(ge=0)
    distance_meters: int = Field(ge=0)


class CandidateRouteMetricsResponseDTO(ModalResponseDTO):
    """추천 장소를 경유하는 양쪽 이동 지표와 시각 응답."""

    previous_to_candidate: RouteLegMetricsResponseDTO
    candidate_to_next: RouteLegMetricsResponseDTO
    candidate_arrival_at: datetime
    candidate_departure_at: datetime
    next_arrival_at: datetime


class RouteLegInsertionImpactResponseDTO(ModalResponseDTO):
    """추천 장소 추가가 전체 일정에 미치는 영향 응답."""

    replacement_travel_minutes: int = Field(ge=0)
    replacement_total_minutes: int = Field(ge=0)
    additional_minutes: int
    updated_next_arrival_at: datetime
    updated_timeline_end_at: datetime
    remaining_minutes: int
    rejection_reasons: list[RouteInsertionRejectionReason]


class CandidateRecommendationResponseDTO(ModalResponseDTO):
    """삽입 가능한 장소 한 개와 평가 결과 응답."""

    candidate: PlaceCandidateResponseDTO
    window: RouteLegInsertionWindowResponseDTO
    route_metrics: CandidateRouteMetricsResponseDTO
    insertion_impact: RouteLegInsertionImpactResponseDTO


class RecommendationGroupResponseDTO(ModalResponseDTO):
    """화면에 표시할 카테고리별 추천 장소 응답."""

    category: RecommendationCategory
    display_name: str = Field(min_length=1)
    recommendations: list[CandidateRecommendationResponseDTO]


class RouteLegGeometryResponseDTO(ModalResponseDTO):
    """Google 지도에 표시할 한 경로 구간 polyline 응답."""

    encoded_polyline: str = Field(min_length=1)


class OptimizedRouteLegGeometryResponseDTO(ModalResponseDTO):
    """최적화 경로 구간 식별 정보와 geometry 응답."""

    day_index: int = Field(ge=1)
    leg_index: int = Field(ge=0)
    origin_place_id: str = Field(min_length=1)
    destination_place_id: str = Field(min_length=1)
    geometry: RouteLegGeometryResponseDTO


class RouteOptionRecommendationResponseDTO(ModalResponseDTO):
    """한 Route Option에 종속된 geometry와 추천 그룹 응답."""

    route_option: RouteOptionDTO
    route_leg_geometries: list[OptimizedRouteLegGeometryResponseDTO]
    recommendation_groups: list[RecommendationGroupResponseDTO]


class RouteOptionRecommendationOutcomeResponseDTO(ModalResponseDTO):
    """사용 불가 이동수단까지 보존하는 옵션별 추천 응답."""

    route_option: RouteOptionDTO
    status: RouteOptionRecommendationStatus
    recommendation: RouteOptionRecommendationResponseDTO | None

    @model_validator(mode="after")
    def validate_status_and_recommendation(self) -> Self:
        if (
            self.status is RouteOptionRecommendationStatus.SUCCESS
            and self.recommendation is None
        ):
            raise ValueError("SUCCESS 결과에는 recommendation이 필요합니다.")
        if (
            self.status is RouteOptionRecommendationStatus.UNAVAILABLE
            and self.recommendation is not None
        ):
            raise ValueError(
                "UNAVAILABLE 결과의 recommendation은 null이어야 합니다."
            )
        if (
            self.status is RouteOptionRecommendationStatus.SUCCESS
            and self.route_option.timeline is None
        ):
            raise ValueError(
                "SUCCESS 추천의 Route Option에는 timeline이 필요합니다."
            )
        if (
            self.status is RouteOptionRecommendationStatus.UNAVAILABLE
            and self.route_option.timeline is not None
        ):
            raise ValueError(
                "UNAVAILABLE 추천의 Route Option timeline은 "
                "null이어야 합니다."
            )
        if (
            self.recommendation is not None
            and self.recommendation.route_option != self.route_option
        ):
            raise ValueError(
                "recommendation과 결과의 Route Option이 일치해야 합니다."
            )
        return self


class DayRouteOptionRecommendationsResponseDTO(ModalResponseDTO):
    """한 여행 일자의 이동수단별 추천 응답."""

    day_index: int = Field(ge=1)
    route_options: list[RouteOptionRecommendationOutcomeResponseDTO]

    @model_validator(mode="after")
    def validate_route_option_day_indexes(self) -> Self:
        if any(
            outcome.route_option.day_index != self.day_index
            for outcome in self.route_options
        ):
            raise ValueError(
                "추천 결과와 Route Option의 day_index가 일치해야 합니다."
            )
        return self


class FreeTimeRecommendationsResponseDTO(ModalResponseDTO):
    """기존 Route Option을 입력받는 독립 추천 API 응답."""

    route_options: list[RouteOptionRecommendationOutcomeResponseDTO]


class TripPlanningWithRecommendationsResponseDTO(ModalResponseDTO):
    """일정 최적화와 날짜별 빈 시간대 추천의 통합 API 응답."""

    trip_id: str = Field(min_length=1)
    status: TripPlanningStatus
    day_plans: list[DayPlanDTO]
    unassigned_pois: list[UnassignedPoiDTO]
    warnings: list[str]
    day_recommendations: list[DayRouteOptionRecommendationsResponseDTO]

    @model_validator(mode="after")
    def validate_day_recommendation_mapping(self) -> Self:
        plan_indexes = [day.day_index for day in self.day_plans]
        recommendation_indexes = [
            day.day_index for day in self.day_recommendations
        ]
        if recommendation_indexes != plan_indexes:
            raise ValueError(
                "day_plans와 day_recommendations의 day_index 순서가 "
                "일치해야 합니다."
            )
        for day_plan, day_recommendation in zip(
            self.day_plans,
            self.day_recommendations,
        ):
            recommendation_options = [
                outcome.route_option
                for outcome in day_recommendation.route_options
            ]
            if recommendation_options != day_plan.route_options:
                raise ValueError(
                    "day_plans와 day_recommendations의 Route Option이 "
                    "일치해야 합니다."
                )
        return self


def to_route_option_recommendation_outcome_response(
    outcome: RouteOptionRecommendationOutcome,
) -> RouteOptionRecommendationOutcomeResponseDTO:
    """Application 추천 결과를 Modal 외부 응답 계약으로 변환한다."""

    recommendation = outcome.recommendation
    return RouteOptionRecommendationOutcomeResponseDTO(
        route_option=outcome.route_option,
        status=outcome.status,
        recommendation=(
            RouteOptionRecommendationResponseDTO.model_validate(
                recommendation,
                from_attributes=True,
            )
            if recommendation is not None
            else None
        ),
    )


def to_trip_planning_with_recommendations_response(
    result: TripPlanWithRecommendations,
) -> TripPlanningWithRecommendationsResponseDTO:
    """Application 통합 결과를 검증 가능한 응답으로 변환한다."""

    if not isinstance(result, TripPlanWithRecommendations):
        raise TypeError("result는 TripPlanWithRecommendations여야 합니다.")

    return TripPlanningWithRecommendationsResponseDTO(
        **result.planning.model_dump(),
        day_recommendations=[
            DayRouteOptionRecommendationsResponseDTO(
                day_index=day.day_index,
                route_options=[
                    to_route_option_recommendation_outcome_response(outcome)
                    for outcome in day.route_options
                ],
            )
            for day in result.day_recommendations
        ],
    )


def to_free_time_recommendations_response(
    outcomes: tuple[RouteOptionRecommendationOutcome, ...],
) -> FreeTimeRecommendationsResponseDTO:
    """독립 추천 결과를 동일한 옵션 응답 계약으로 변환한다."""

    if not isinstance(outcomes, tuple):
        raise TypeError("outcomes는 tuple이어야 합니다.")
    return FreeTimeRecommendationsResponseDTO(
        route_options=[
            to_route_option_recommendation_outcome_response(outcome)
            for outcome in outcomes
        ]
    )
