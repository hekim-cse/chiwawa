from pydantic import Field

from chiwawa_backend.schemas.base import ApiModel, PlaceSource


class PhotoPlaceSearchRequest(ApiModel):
    image_url: str | None = Field(default=None, min_length=1)
    note: str | None = Field(default=None, min_length=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class PhotoPlaceCandidateRead(ApiModel):
    id: str
    name: str
    city: str
    country: str
    latitude: float
    longitude: float
    confidence: float = Field(ge=0, le=1)
    reason: str


class PhotoPlaceSearchResponse(ApiModel):
    id: str
    trip_id: str
    candidates: list[PhotoPlaceCandidateRead]


class WantedPlaceCreateRequest(ApiModel):
    name: str = Field(min_length=1)
    city: str | None = Field(default=None, min_length=1)
    country: str = Field(default="Japan", min_length=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    priority: int = Field(default=3, ge=1, le=5)
    notes: str | None = Field(default=None, min_length=1)


class WantedPlaceUpdateRequest(ApiModel):
    name: str | None = Field(default=None, min_length=1)
    city: str | None = Field(default=None, min_length=1)
    country: str | None = Field(default=None, min_length=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    priority: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = Field(default=None, min_length=1)


class WantedPlaceRead(ApiModel):
    id: str
    trip_id: str
    name: str
    city: str
    country: str
    latitude: float | None
    longitude: float | None
    priority: int
    notes: str | None
    source: PlaceSource


class WantedPlaceListResponse(ApiModel):
    items: list[WantedPlaceRead]


class PhotoPlaceConfirmRequest(ApiModel):
    candidate_id: str = Field(min_length=1)


class ConfirmedPhotoPlaceRead(ApiModel):
    search_id: str
    candidate: PhotoPlaceCandidateRead
    wanted_place: WantedPlaceRead
