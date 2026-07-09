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
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


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


class TripPlanningDayPlan(ApiModel):
    day_index: int = Field(ge=1)
    date: dt.date
    start_place: TripPlanningPlace
    end_place: TripPlanningPlace
    assigned_pois: list[TripPlanningPOI]
    estimated_total_stay_minutes: int = Field(ge=0)
    assignment_reason: str = Field(min_length=1)


class TripPlanningUnassignedPOI(ApiModel):
    poi: TripPlanningPOI
    reason: str = Field(min_length=1)


class TripPlanningResponse(ApiModel):
    trip_id: str = Field(min_length=1)
    status: TripPlanningStatus
    day_plans: list[TripPlanningDayPlan] = Field(default_factory=list)
    unassigned_pois: list[TripPlanningUnassignedPOI] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
