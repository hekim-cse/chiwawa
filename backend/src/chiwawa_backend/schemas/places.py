from typing import Annotated, Self

from pydantic import Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from chiwawa_backend.schemas.base import ApiModel, PlaceSource
from chiwawa_backend.schemas.patch_validation import (
    reject_explicit_null,
    require_coordinate_pair,
)

WANTED_REQUIRED_PATCH_FIELDS = frozenset({"name", "city", "country", "priority"})


class PhotoPlaceSearchRequest(ApiModel):
    image_url: str | None = Field(default=None, min_length=1)
    note: str | None = Field(default=None, min_length=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def require_paired_coordinates(self) -> Self:
        require_coordinate_pair(self, self.latitude, self.longitude)
        return self


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

    @model_validator(mode="after")
    def require_paired_coordinates(self) -> Self:
        require_coordinate_pair(self, self.latitude, self.longitude)
        return self


class WantedPlaceUpdateRequest(ApiModel):
    name: Annotated[str, Field(min_length=1)] | SkipJsonSchema[None] = None
    city: Annotated[str, Field(min_length=1)] | SkipJsonSchema[None] = None
    country: Annotated[str, Field(min_length=1)] | SkipJsonSchema[None] = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    priority: Annotated[int, Field(ge=1, le=5)] | SkipJsonSchema[None] = None
    notes: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        reject_explicit_null(self, WANTED_REQUIRED_PATCH_FIELDS)
        require_coordinate_pair(self, self.latitude, self.longitude)
        return self


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
