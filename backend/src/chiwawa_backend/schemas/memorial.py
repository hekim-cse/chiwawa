import datetime as dt
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from chiwawa_backend.schemas.base import ApiModel
from chiwawa_backend.schemas.patch_validation import (
    reject_explicit_null,
    require_coordinate_pair,
)


class MemorialPhotoUploadRequest(ApiModel):
    device_photo_id: str | None = Field(default=None, min_length=1, max_length=255)
    file_name: str = Field(min_length=1)
    taken_at: dt.datetime | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    memo: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_paired_coordinates(self) -> Self:
        require_coordinate_pair(self, self.latitude, self.longitude)
        return self


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
    title: Annotated[str, Field(min_length=1)] | SkipJsonSchema[None] = None
    summary: Annotated[str, Field(min_length=1)] | SkipJsonSchema[None] = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        reject_explicit_null(self, frozenset({"title", "summary"}))
        return self


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
    taken_at: dt.datetime | SkipJsonSchema[None] = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    memo: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        reject_explicit_null(self, frozenset({"taken_at"}))
        require_coordinate_pair(self, self.latitude, self.longitude)
        return self
