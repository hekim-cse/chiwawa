from datetime import date
from typing import Self

from pydantic import Field, model_validator

from chiwawa_backend.schemas.base import ApiModel, TravelStyle


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
        return self


class TripUpdateRequest(ApiModel):
    city: str | None = Field(default=None, min_length=1)
    country: str | None = Field(default=None, min_length=1)
    start_date: date | None = None
    end_date: date | None = None
    travelers: int | None = Field(default=None, ge=1)
    interests: list[str] | None = None
    travel_style: TravelStyle | None = None
    title: str | None = Field(default=None, min_length=1)


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
