# Image Search Modal과 Backend 사이의 독립 HTTP 계약
from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from chiwawa_backend.schemas.base import ApiModel


class ImageSearchRequest(ApiModel):
    image_url: str | None = Field(default=None, min_length=1)
    image_base64: str | None = Field(default=None, min_length=1)
    image_mime_type: str | None = Field(default=None, pattern=r"^image/")
    note: str | None = Field(default=None, min_length=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    city: str | None = Field(default=None, min_length=1)
    country: str | None = Field(default=None, min_length=1)
    max_candidates: int = Field(default=5, ge=1)

    @model_validator(mode="after")
    def require_image_source(self) -> Self:
        if self.image_url is None and self.image_base64 is None:
            message = "image_url 또는 image_base64 중 하나는 필요합니다."
            raise ValueError(message)
        return self


class ImageSearchCandidate(ApiModel):
    name: str
    city: str
    country: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    confidence: float = Field(ge=0, le=1)
    reason: str
    category: str
    source: str
    place_id: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)


class ImageSearchResult(ApiModel):
    identified: ImageSearchCandidate | None
    candidates: list[ImageSearchCandidate] = Field(default_factory=list)
    status: str
    signals: dict[str, object] = Field(default_factory=dict)
