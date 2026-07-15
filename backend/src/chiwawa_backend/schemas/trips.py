from datetime import date
from typing import Annotated, Self

from pydantic import Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from chiwawa_backend.schemas.base import ApiModel, TravelStyle
from chiwawa_backend.schemas.patch_validation import reject_explicit_null

MAX_TRIP_DAYS = 31
TRIP_REQUIRED_PATCH_FIELDS = frozenset(
    {
        "city",
        "country",
        "start_date",
        "end_date",
        "travelers",
        "interests",
        "travel_style",
        "title",
    },
)


class TripCreateRequest(ApiModel):
    city: str = Field(min_length=1)
    country: str = Field(default="Japan", min_length=1)
    start_date: date
    end_date: date
    travelers: int = Field(default=1, ge=1)
    interests: list[str] = Field(default_factory=list)
    travel_style: TravelStyle = TravelStyle.BALANCED
    title: str | None = None

    @model_validator(mode="after")
    def require_ordered_dates(self) -> Self:
        if self.end_date < self.start_date:
            msg = "end_date must be greater than or equal to start_date"
            raise ValueError(msg)
        if (self.end_date - self.start_date).days >= MAX_TRIP_DAYS:
            msg = f"trip duration must not exceed {MAX_TRIP_DAYS} days"
            raise ValueError(msg)
        return self


class TripUpdateRequest(ApiModel):
    city: Annotated[str, Field(min_length=1)] | SkipJsonSchema[None] = None
    country: Annotated[str, Field(min_length=1)] | SkipJsonSchema[None] = None
    start_date: date | SkipJsonSchema[None] = None
    end_date: date | SkipJsonSchema[None] = None
    travelers: Annotated[int, Field(ge=1)] | SkipJsonSchema[None] = None
    interests: list[str] | SkipJsonSchema[None] = None
    travel_style: TravelStyle | SkipJsonSchema[None] = None
    title: Annotated[str, Field(min_length=1)] | SkipJsonSchema[None] = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        reject_explicit_null(self, TRIP_REQUIRED_PATCH_FIELDS)
        return self


class TripRead(ApiModel):
    id: str
    title: str
    city: str
    country: str
    start_date: date
    end_date: date
    travelers: int
    interests: list[str]
    travel_style: TravelStyle


class TripListResponse(ApiModel):
    items: list[TripRead]
