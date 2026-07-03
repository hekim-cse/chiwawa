import datetime as dt

from pydantic import Field

from chiwawa_backend.schemas.base import (
    ApiModel,
    PlaceSource,
    PlanJobStatus,
    TravelStyle,
)
from chiwawa_backend.schemas.schedule import ScheduleResponse


class AIPlanCreateRequest(ApiModel):
    preferred_start_time: dt.time = dt.time(hour=9)
    preferred_end_time: dt.time = dt.time(hour=21)
    pace: TravelStyle | None = None


class PlanJobRead(ApiModel):
    id: str
    trip_id: str
    status: PlanJobStatus
    plan_id: str | None
    message: str


class PlanStopRead(ApiModel):
    id: str
    place_id: str | None
    name: str
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    notes: str | None
    source: PlaceSource


class PlanDayRead(ApiModel):
    date: dt.date
    stops: list[PlanStopRead]


class PlanDraftRead(ApiModel):
    id: str
    trip_id: str
    title: str
    days: list[PlanDayRead]
    estimated_total_minutes: int = Field(ge=0)


class PlanConfirmResponse(ApiModel):
    plan: PlanDraftRead
    schedule: ScheduleResponse


class RouteOptimizationRequest(ApiModel):
    start_place: str | None = Field(default=None, min_length=1)
    transport_mode: str = Field(default="transit", min_length=1)


class RouteStopRead(ApiModel):
    order: int = Field(ge=1)
    place_id: str
    name: str
    estimated_travel_minutes: int = Field(ge=0)


class RouteOptimizationResponse(ApiModel):
    trip_id: str
    transport_mode: str
    stops: list[RouteStopRead]
    total_estimated_minutes: int = Field(ge=0)
