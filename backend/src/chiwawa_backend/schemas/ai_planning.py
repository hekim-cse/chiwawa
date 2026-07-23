import datetime as dt
from enum import StrEnum
from typing import Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_serializer, field_validator
from pydantic_core import PydanticCustomError

from chiwawa_backend.schemas.base import ApiModel

INVALID_TIMEZONE_CODE: Final = "timezone"
INVALID_TIMEZONE_MESSAGE: Final = "timezone must be a valid IANA timezone"
INVALID_TIME_PRECISION_CODE: Final = "time_precision"
INVALID_TIME_PRECISION_MESSAGE: Final = "time must use HH:MM minute precision"


class TripPlanningStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class TravelMode(StrEnum):
    DRIVE = "DRIVE"
    WALK = "WALK"
    TRANSIT = "TRANSIT"


class RecommendationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    UNAVAILABLE = "UNAVAILABLE"


# AI 계약과 동일 값 (직접 import 하지 않고 백엔드에 복제 정의).
class RecommendationCategory(StrEnum):
    LANDMARK = "LANDMARK"
    CAFE = "CAFE"
    CULTURE = "CULTURE"
    PARK = "PARK"
    RESTAURANT = "RESTAURANT"


class RouteInsertionRejectionReason(StrEnum):
    STAY_DURATION_BELOW_MINIMUM = "STAY_DURATION_BELOW_MINIMUM"
    PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED = "PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED"
    CANDIDATE_TO_NEXT_LIMIT_EXCEEDED = "CANDIDATE_TO_NEXT_LIMIT_EXCEEDED"
    PREVIOUS_TO_CANDIDATE_DISTANCE_LIMIT_EXCEEDED = (
        "PREVIOUS_TO_CANDIDATE_DISTANCE_LIMIT_EXCEEDED"
    )
    CANDIDATE_TO_NEXT_DISTANCE_LIMIT_EXCEEDED = (
        "CANDIDATE_TO_NEXT_DISTANCE_LIMIT_EXCEEDED"
    )
    PLANNED_END_EXCEEDED = "PLANNED_END_EXCEEDED"


class TripPlanningPlace(ApiModel):
    place_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class TripPlanningPOI(ApiModel):
    poi_id: str = Field(min_length=1)
    place_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    category: str = Field(min_length=1)
    estimated_stay_minutes: int = Field(ge=1)
    priority: int = Field(ge=1, le=5)
    must_visit: bool
    preferred_day_index: int | None = Field(default=None, ge=1)


class TripPlanningDayConstraint(ApiModel):
    day_index: int = Field(ge=1)
    date: dt.date
    start_place: TripPlanningPlace
    start_time: dt.time
    end_place: TripPlanningPlace
    end_time: dt.time
    max_place_count: int | None = Field(default=None, ge=1)

    @field_validator("start_time", "end_time")
    @classmethod
    def require_minute_precision(cls, value: dt.time) -> dt.time:
        if value.second != 0 or value.microsecond != 0:
            raise PydanticCustomError(
                INVALID_TIME_PRECISION_CODE,
                INVALID_TIME_PRECISION_MESSAGE,
            )
        return value

    @field_serializer("start_time", "end_time")
    def serialize_minute_time(self, value: dt.time) -> str:
        _ = self
        return value.strftime("%H:%M")


class TripPlanningRequest(ApiModel):
    trip_id: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    days: list[TripPlanningDayConstraint] = Field(min_length=1)
    pois: list[TripPlanningPOI]

    @field_validator("timezone")
    @classmethod
    def require_iana_timezone(cls, value: str) -> str:
        try:
            _ = ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise PydanticCustomError(
                INVALID_TIMEZONE_CODE,
                INVALID_TIMEZONE_MESSAGE,
            ) from exc
        return value


class RouteStopRead(ApiModel):
    stop_type: str = Field(min_length=1)
    place_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class RouteLegRead(ApiModel):
    origin_place_id: str = Field(min_length=1)
    destination_place_id: str = Field(min_length=1)
    travel_minutes: int


class TimelineStopRead(ApiModel):
    stop_type: str = Field(min_length=1)
    place_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arrival_at: str = Field(min_length=1)
    departure_at: str = Field(min_length=1)
    stay_minutes: int = Field(ge=0)


class TimelineRead(ApiModel):
    day_index: int = Field(ge=1)
    travel_mode: TravelMode
    planned_start_at: str = Field(min_length=1)
    planned_end_at: str = Field(min_length=1)
    actual_end_at: str = Field(min_length=1)
    total_travel_minutes: int = Field(ge=0)
    total_stay_minutes: int = Field(ge=0)
    timeline_stops: list[TimelineStopRead]
    exceeds_planned_end: bool = False
    warnings: list[str] = Field(default_factory=list)


class RouteOptionRead(ApiModel):
    day_index: int = Field(ge=1)
    travel_mode: TravelMode
    total_travel_minutes: int = Field(ge=0)
    ordered_stops: list[RouteStopRead]
    route_legs: list[RouteLegRead]
    missing_segments: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    timeline: TimelineRead | None = None


class TripPlanningDayPlan(ApiModel):
    day_index: int = Field(ge=1)
    date: dt.date
    start_place: TripPlanningPlace
    end_place: TripPlanningPlace
    assigned_pois: list[TripPlanningPOI]
    estimated_total_stay_minutes: int = Field(ge=0)
    assignment_reason: str = Field(min_length=1)
    route_options: list[RouteOptionRead] = Field(default_factory=list)


class TripPlanningUnassignedPOI(ApiModel):
    poi: TripPlanningPOI
    reason: str = Field(min_length=1)


class TripPlanningResponse(ApiModel):
    trip_id: str = Field(min_length=1)
    status: TripPlanningStatus
    day_plans: list[TripPlanningDayPlan] = Field(default_factory=list)
    unassigned_pois: list[TripPlanningUnassignedPOI] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Coordinate(ApiModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class CandidatePlace(ApiModel):
    place_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    coordinate: Coordinate
    category: RecommendationCategory
    formatted_address: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    user_rating_count: int | None = Field(default=None, ge=0)


class RecommendationWindow(ApiModel):
    day_index: int = Field(ge=1)
    leg_index: int = Field(ge=0)
    previous_place_id: str = Field(min_length=1)
    next_place_id: str = Field(min_length=1)
    previous_departure_at: dt.datetime
    next_arrival_at: dt.datetime
    original_travel_minutes: int = Field(ge=0)
    original_timeline_end_at: dt.datetime
    planned_end_at: dt.datetime


class TravelMetric(ApiModel):
    travel_minutes: int = Field(ge=0)
    distance_meters: int = Field(ge=0)


class RouteMetrics(ApiModel):
    previous_to_candidate: TravelMetric
    candidate_to_next: TravelMetric
    candidate_arrival_at: dt.datetime
    candidate_departure_at: dt.datetime
    next_arrival_at: dt.datetime


class InsertionImpact(ApiModel):
    replacement_travel_minutes: int
    replacement_total_minutes: int
    additional_minutes: int
    updated_next_arrival_at: dt.datetime
    updated_timeline_end_at: dt.datetime
    remaining_minutes: int
    rejection_reasons: list[RouteInsertionRejectionReason] = Field(
        default_factory=list,
    )


class CandidateRecommendationRead(ApiModel):
    candidate: CandidatePlace
    window: RecommendationWindow
    route_metrics: RouteMetrics
    insertion_impact: InsertionImpact


class RecommendationGroupRead(ApiModel):
    category: RecommendationCategory
    display_name: str = Field(min_length=1)
    recommendations: list[CandidateRecommendationRead]


class RouteLegGeometryRead(ApiModel):
    encoded_polyline: str = Field(min_length=1)


class OptimizedRouteLegGeometryRead(ApiModel):
    day_index: int = Field(ge=1)
    leg_index: int = Field(ge=0)
    origin_place_id: str = Field(min_length=1)
    destination_place_id: str = Field(min_length=1)
    geometry: RouteLegGeometryRead


class RecommendationRead(ApiModel):
    route_option: RouteOptionRead
    route_leg_geometries: list[OptimizedRouteLegGeometryRead] = Field(
        default_factory=list,
    )
    recommendation_groups: list[RecommendationGroupRead]


class DayRecommendationRouteOptionRead(ApiModel):
    route_option: RouteOptionRead
    status: RecommendationStatus
    recommendation: RecommendationRead | None = None


class DayRecommendationsRead(ApiModel):
    day_index: int = Field(ge=1)
    route_options: list[DayRecommendationRouteOptionRead]


class TripPlanningWithRecommendationsResponse(ApiModel):
    trip_id: str = Field(min_length=1)
    status: TripPlanningStatus
    day_plans: list[TripPlanningDayPlan] = Field(default_factory=list)
    unassigned_pois: list[TripPlanningUnassignedPOI] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    day_recommendations: list[DayRecommendationsRead] = Field(default_factory=list)
