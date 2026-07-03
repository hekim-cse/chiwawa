import datetime as dt

from pydantic import Field

from chiwawa_backend.schemas.base import ApiModel
from chiwawa_backend.schemas.plans import PlanDraftRead
from chiwawa_backend.schemas.schedule import ScheduleItemRead, ScheduleResponse


class TodayScheduleResponse(ApiModel):
    trip_id: str
    date: dt.date
    schedule: ScheduleResponse


class FreeTimeRecommendationRequest(ApiModel):
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    current_area: str | None = Field(default=None, min_length=1)


class FreeTimeRecommendationRead(ApiModel):
    id: str
    trip_id: str
    title: str
    place_name: str
    duration_minutes: int = Field(ge=1)
    reason: str
    date: dt.date
    start_time: dt.time
    end_time: dt.time


class FreeTimeRecommendationResponse(ApiModel):
    trip_id: str
    items: list[FreeTimeRecommendationRead]


class AddRecommendationResponse(ApiModel):
    schedule_item: ScheduleItemRead


class NearbyRecommendationRequest(ApiModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    theme: str | None = Field(default=None, min_length=1)


class NearbyRecommendationRead(ApiModel):
    title: str
    place_name: str
    estimated_walk_minutes: int = Field(ge=1)
    reason: str


class NearbyRecommendationResponse(ApiModel):
    trip_id: str
    items: list[NearbyRecommendationRead]


class ReplanRequest(ApiModel):
    delay_minutes: int = Field(default=0, ge=0)
    current_item_id: str | None = Field(default=None, min_length=1)
    reason: str | None = Field(default=None, min_length=1)


class ReplanResponse(ApiModel):
    plan: PlanDraftRead
    message: str
