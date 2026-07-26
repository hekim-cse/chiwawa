# Flutter 출발지·도착지 선택용 일반 장소 검색 Endpoint
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from chiwawa_backend.dependencies import get_place_search_provider
from chiwawa_backend.errors import DomainValidationError
from chiwawa_backend.schemas.place_search import PlaceSearchResponse
from chiwawa_backend.services.place_search import PlaceSearchProvider

router = APIRouter(prefix="/api/v1/places", tags=["places"])
BLANK_PLACE_QUERY_MESSAGE = "장소 검색어는 비어 있을 수 없습니다."
PlaceSearchProviderDep = Annotated[
    PlaceSearchProvider,
    Depends(get_place_search_provider),
]


@router.get("/search")
async def search_places(
    provider: PlaceSearchProviderDep,
    query: Annotated[str, Query(min_length=1, max_length=100)],
    city_bias: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> PlaceSearchResponse:
    normalized_query = query.strip()
    if not normalized_query:
        raise DomainValidationError(BLANK_PLACE_QUERY_MESSAGE)
    items = await provider.search(
        query=normalized_query,
        city_bias=city_bias.strip() if city_bias is not None else None,
    )
    return PlaceSearchResponse(items=list(items))
