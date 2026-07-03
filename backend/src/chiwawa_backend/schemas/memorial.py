import datetime as dt

from pydantic import Field

from chiwawa_backend.schemas.base import ApiModel


class MemorialPhotoUploadRequest(ApiModel):
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
