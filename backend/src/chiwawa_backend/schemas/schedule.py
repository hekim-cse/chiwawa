import datetime as dt
from typing import Annotated, Self

from pydantic import Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from chiwawa_backend.schemas.base import ApiModel, PlaceSource
from chiwawa_backend.schemas.patch_validation import reject_explicit_null

SCHEDULE_REQUIRED_PATCH_FIELDS = frozenset(
    {"name", "date", "start_time", "end_time", "source"},
)


class ScheduleItemCreateRequest(ApiModel):
    name: str = Field(min_length=1)
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    place_id: str | None = Field(default=None, min_length=1)
    notes: str | None = Field(default=None, min_length=1)
    source: PlaceSource = PlaceSource.MANUAL

    @model_validator(mode="after")
    def require_ordered_times(self) -> Self:
        if self.start_time.tzinfo is not None or self.end_time.tzinfo is not None:
            msg = "timezone offsets are not allowed"
            raise ValueError(msg)
        if self.end_time <= self.start_time:
            msg = "end_time must be after start_time"
            raise ValueError(msg)
        return self


class ScheduleItemUpdateRequest(ApiModel):
    name: Annotated[str, Field(min_length=1)] | SkipJsonSchema[None] = None
    date: dt.date | SkipJsonSchema[None] = None
    start_time: dt.time | SkipJsonSchema[None] = None
    end_time: dt.time | SkipJsonSchema[None] = None
    place_id: str | None = Field(default=None, min_length=1)
    notes: str | None = Field(default=None, min_length=1)
    source: PlaceSource | SkipJsonSchema[None] = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        reject_explicit_null(self, SCHEDULE_REQUIRED_PATCH_FIELDS)
        return self


class ScheduleItemRead(ApiModel):
    id: str
    trip_id: str
    name: str
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    place_id: str | None
    notes: str | None
    source: PlaceSource


class ScheduleResponse(ApiModel):
    trip_id: str
    items: list[ScheduleItemRead]
