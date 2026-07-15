import datetime as dt
import re
from enum import StrEnum
from itertools import pairwise
from typing import Final, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_serializer, field_validator, model_validator
from pydantic_core import PydanticCustomError

from chiwawa_backend.schemas.base import ApiModel

INVALID_TIMEZONE_CODE: Final = "timezone"
INVALID_TIMEZONE_MESSAGE: Final = "timezone must be a valid IANA timezone"
INVALID_TIME_PRECISION_CODE: Final = "time_precision"
INVALID_TIME_PRECISION_MESSAGE: Final = "time must use HH:MM minute precision"
MINUTE_TIME_PATTERN: Final = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z")
type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


class TripPlanningStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class TripPlanningPOICategory(StrEnum):
    TOURIST_ATTRACTION = "TOURIST_ATTRACTION"
    RESTAURANT = "RESTAURANT"
    CAFE = "CAFE"
    SHOPPING = "SHOPPING"
    ACTIVITY = "ACTIVITY"
    HOTEL = "HOTEL"
    ETC = "ETC"


class TripPlanningTravelMode(StrEnum):
    WALK = "WALK"
    DRIVE = "DRIVE"
    TRANSIT = "TRANSIT"


class TripPlanningRouteStopType(StrEnum):
    START = "START"
    POI = "POI"
    END = "END"


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
    category: TripPlanningPOICategory = TripPlanningPOICategory.ETC
    estimated_stay_minutes: int = Field(ge=1)
    priority: int = Field(default=3, ge=1, le=5)
    must_visit: bool = True
    preferred_day_index: int | None = Field(default=None, ge=1)


class TripPlanningDayConstraint(ApiModel):
    day_index: int = Field(ge=1)
    date: dt.date
    start_place: TripPlanningPlace
    start_time: dt.time
    end_place: TripPlanningPlace
    end_time: dt.time
    max_place_count: int | None = Field(default=None, ge=1)

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def require_minute_wire_time(cls, value: JsonValue) -> str:
        if not isinstance(value, str) or MINUTE_TIME_PATTERN.fullmatch(value) is None:
            raise PydanticCustomError(
                INVALID_TIME_PRECISION_CODE,
                INVALID_TIME_PRECISION_MESSAGE,
            )
        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def require_minute_precision(cls, value: dt.time) -> dt.time:
        if value.tzinfo is not None:
            message = "timezone offsets are not allowed"
            raise ValueError(message)
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

    @model_validator(mode="after")
    def require_forward_time_window(self) -> Self:
        if self.end_time <= self.start_time:
            message = "end_time must be after start_time"
            raise ValueError(message)
        return self


class TripPlanningRequest(ApiModel):
    trip_id: str = Field(min_length=1)
    timezone: str = Field(default="Asia/Tokyo", min_length=1)
    days: list[TripPlanningDayConstraint] = Field(min_length=1)
    pois: list[TripPlanningPOI] = Field(min_length=1)

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

    @model_validator(mode="after")
    def require_consistent_days(self) -> Self:
        ordered_days = sorted(self.days, key=lambda day: day.day_index)
        indexes = [day.day_index for day in ordered_days]
        if indexes != list(range(1, len(ordered_days) + 1)):
            message = "day_index values must be unique and contiguous"
            raise ValueError(message)
        dates = [day.date for day in ordered_days]
        if len(dates) != len(set(dates)):
            message = "day dates must be unique"
            raise ValueError(message)
        if any(left >= right for left, right in pairwise(dates)):
            message = "day dates must increase with day_index"
            raise ValueError(message)
        valid_indexes = set(indexes)
        if any(
            poi.preferred_day_index is not None
            and poi.preferred_day_index not in valid_indexes
            for poi in self.pois
        ):
            message = "preferred_day_index must reference an existing day"
            raise ValueError(message)
        return self


class TripPlanningRouteStop(ApiModel):
    stop_type: TripPlanningRouteStopType
    place_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class TripPlanningRouteLeg(ApiModel):
    origin_place_id: str = Field(min_length=1)
    destination_place_id: str = Field(min_length=1)
    travel_minutes: int = Field(ge=0)


class TripPlanningTimelineStop(ApiModel):
    stop_type: TripPlanningRouteStopType
    place_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arrival_at: str = Field(min_length=1)
    departure_at: str = Field(min_length=1)
    stay_minutes: int = Field(ge=0)


class TripPlanningTimeline(ApiModel):
    day_index: int = Field(ge=1)
    travel_mode: TripPlanningTravelMode
    planned_start_at: str = Field(min_length=1)
    planned_end_at: str = Field(min_length=1)
    actual_end_at: str = Field(min_length=1)
    total_travel_minutes: int = Field(ge=0)
    total_stay_minutes: int = Field(ge=0)
    timeline_stops: list[TripPlanningTimelineStop]
    exceeds_planned_end: bool = False
    warnings: list[str] = Field(default_factory=list)


class TripPlanningRouteOption(ApiModel):
    day_index: int = Field(ge=1)
    travel_mode: TripPlanningTravelMode
    total_travel_minutes: int = Field(ge=0)
    ordered_stops: list[TripPlanningRouteStop]
    route_legs: list[TripPlanningRouteLeg]
    missing_segments: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    timeline: TripPlanningTimeline | None = None

    @model_validator(mode="after")
    def require_matching_timeline(self) -> Self:
        if self.timeline is None:
            return self
        if (
            self.timeline.day_index != self.day_index
            or self.timeline.travel_mode is not self.travel_mode
        ):
            message = "timeline must match its route option"
            raise ValueError(message)
        return self


class TripPlanningDayPlan(ApiModel):
    day_index: int = Field(ge=1)
    date: dt.date
    start_place: TripPlanningPlace
    end_place: TripPlanningPlace
    assigned_pois: list[TripPlanningPOI]
    estimated_total_stay_minutes: int = Field(ge=0)
    assignment_reason: str = Field(min_length=1)
    route_options: list[TripPlanningRouteOption] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_matching_route_days(self) -> Self:
        if any(option.day_index != self.day_index for option in self.route_options):
            message = "route option must match its day plan"
            raise ValueError(message)
        return self


class TripPlanningUnassignedPOI(ApiModel):
    poi: TripPlanningPOI
    reason: str = Field(min_length=1)


class TripPlanningResponse(ApiModel):
    trip_id: str = Field(min_length=1)
    status: TripPlanningStatus
    day_plans: list[TripPlanningDayPlan]
    unassigned_pois: list[TripPlanningUnassignedPOI] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
