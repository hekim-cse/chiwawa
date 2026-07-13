import datetime as dt
from typing import Self

from pydantic import Field, model_validator

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

    @model_validator(mode="after")
    def require_ordered_times(self) -> Self:
        if (
            self.preferred_start_time.tzinfo is not None
            or self.preferred_end_time.tzinfo is not None
        ):
            msg = "timezone offsets are not allowed"
            raise ValueError(msg)
        if self.preferred_end_time <= self.preferred_start_time:
            msg = "preferred_end_time must be after preferred_start_time"
            raise ValueError(msg)
        duration = dt.datetime.combine(
            dt.date.min,
            self.preferred_end_time,
        ) - dt.datetime.combine(dt.date.min, self.preferred_start_time)
        if duration < dt.timedelta(minutes=1):
            msg = "preferred time window must be at least one minute"
            raise ValueError(msg)
        return self


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
