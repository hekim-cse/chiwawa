import datetime as dt
from typing import Literal

from pydantic import Field

from chiwawa_backend.schemas.base import ApiModel


class MemorialPhotoUploadRequest(ApiModel):
    device_photo_id: str | None = Field(default=None, min_length=1, max_length=255)
    file_name: str = Field(min_length=1)
    taken_at: dt.datetime | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    memo: str | None = Field(default=None, min_length=1)


class MemorialPhotoRead(ApiModel):
    id: str
    trip_id: str
    file_name: str
    taken_at: dt.datetime | None
    latitude: float | None
    longitude: float | None
    memo: str | None
    device_photo_id: str | None = None
    storage: Literal["device"] = "device"


class MemorialPhotoListResponse(ApiModel):
    trip_id: str
    items: list[MemorialPhotoRead]


class MemorialGenerateRequest(ApiModel):
    title: str | None = Field(default=None, min_length=1)


class MemorialRecordRead(ApiModel):
    id: str
    trip_id: str
    title: str
    summary: str
    timeline: list[str]
    photo_count: int = Field(ge=0)


class MemorialUpdateRequest(ApiModel):
    title: str | None = Field(default=None, min_length=1)
    summary: str | None = Field(default=None, min_length=1)


class MemorialPhotoItem(ApiModel):
    """회원 단위 memorial에 저장된 사진 한 장의 메타데이터."""

    id: int
    file_name: str
    content_type: str
    taken_at: dt.datetime
    latitude: float | None
    longitude: float | None
    address: str | None
    memo: str | None
    file_url: str
    created_at: dt.datetime


class MemorialCalendarDay(ApiModel):
    day: dt.date
    photo_count: int = Field(ge=1)


class MemorialCalendarResponse(ApiModel):
    year: int
    month: int
    days: list[MemorialCalendarDay]


class MemorialTimelineEntry(ApiModel):
    """seq 순서대로 지도 위 발자국을 찍는다 (0부터 시작)."""

    seq: int = Field(ge=0)
    photo: MemorialPhotoItem


class MemorialDayResponse(ApiModel):
    day: dt.date
    items: list[MemorialTimelineEntry]


class MemorialPhotoPatchRequest(ApiModel):
    taken_at: dt.datetime | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    memo: str | None = Field(default=None, min_length=1)
