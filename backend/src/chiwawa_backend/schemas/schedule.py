import datetime as dt

from pydantic import Field

from chiwawa_backend.schemas.base import ApiModel, PlaceSource


class ScheduleItemCreateRequest(ApiModel):
    name: str = Field(min_length=1)
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    place_id: str | None = Field(default=None, min_length=1)
    notes: str | None = Field(default=None, min_length=1)
    source: PlaceSource = PlaceSource.MANUAL


class ScheduleItemUpdateRequest(ApiModel):
    name: str | None = Field(default=None, min_length=1)
    date: dt.date | None = None
    start_time: dt.time | None = None
    end_time: dt.time | None = None
    place_id: str | None = Field(default=None, min_length=1)
    notes: str | None = Field(default=None, min_length=1)
    source: PlaceSource | None = None


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
