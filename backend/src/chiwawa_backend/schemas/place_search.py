# 일반 장소 검색 HTTP 요청·응답 계약
from pydantic import Field

from chiwawa_backend.schemas.base import ApiModel


class PlaceSearchCandidateRead(ApiModel):
    provider_place_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    formatted_address: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class PlaceSearchResponse(ApiModel):
    items: list[PlaceSearchCandidateRead]
