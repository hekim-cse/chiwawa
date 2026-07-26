# Google Places Text Search를 사용하는 일반 장소 검색 Provider
from __future__ import annotations

from typing import TYPE_CHECKING, cast

import httpx
from pydantic import ValidationError

from chiwawa_backend.errors import UpstreamServiceError
from chiwawa_backend.schemas.place_search import PlaceSearchCandidateRead

if TYPE_CHECKING:
    from chiwawa_backend.config import Settings

GOOGLE_PLACE_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACE_SEARCH_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location"
)
PLACE_SEARCH_REQUEST_ERROR_MESSAGE = "Google 장소 검색 요청에 실패했습니다."
PLACE_SEARCH_RESPONSE_ERROR_MESSAGE = "Google 장소 검색 응답 계약이 올바르지 않습니다."
PLACE_SEARCH_HTTP_ERROR_MESSAGE = (
    "Google 장소 검색 서비스가 오류를 반환했습니다. HTTP {status_code}"
)


class GooglePlaceSearchProvider:
    """한국어 표시 언어로 전 세계 장소 후보를 조회하는 외부 경계."""

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key: str = settings.require_google_maps_api_key()
        self._timeout: float = settings.place_search_timeout_seconds
        self._page_size: int = settings.place_search_page_size
        self._transport: httpx.AsyncBaseTransport | None = transport

    async def search(
        self,
        *,
        query: str,
        city_bias: str | None,
    ) -> tuple[PlaceSearchCandidateRead, ...]:
        text_query = query if city_bias is None else f"{query} {city_bias}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": GOOGLE_PLACE_SEARCH_FIELD_MASK,
        }
        payload = {
            "textQuery": text_query,
            "pageSize": self._page_size,
            "languageCode": "ko",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    GOOGLE_PLACE_SEARCH_URL,
                    headers=headers,
                    json=payload,
                )
        except httpx.RequestError as error:
            raise UpstreamServiceError(
                PLACE_SEARCH_REQUEST_ERROR_MESSAGE,
            ) from error
        if response.is_error:
            message = PLACE_SEARCH_HTTP_ERROR_MESSAGE.format(
                status_code=response.status_code,
            )
            raise UpstreamServiceError(message)
        return self._parse_response(response)

    @staticmethod
    def _parse_response(
        response: httpx.Response,
    ) -> tuple[PlaceSearchCandidateRead, ...]:
        try:
            payload = cast("object", response.json())
        except ValueError as error:
            raise UpstreamServiceError(
                PLACE_SEARCH_RESPONSE_ERROR_MESSAGE,
            ) from error
        if not isinstance(payload, dict):
            raise UpstreamServiceError(PLACE_SEARCH_RESPONSE_ERROR_MESSAGE)
        places_value = cast("dict[str, object]", payload).get("places", [])
        if not isinstance(places_value, list):
            raise UpstreamServiceError(PLACE_SEARCH_RESPONSE_ERROR_MESSAGE)
        places = cast("list[object]", places_value)

        try:
            candidates = [
                GooglePlaceSearchProvider._parse_place(place) for place in places
            ]
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise UpstreamServiceError(
                PLACE_SEARCH_RESPONSE_ERROR_MESSAGE,
            ) from error
        return tuple(candidates)

    @staticmethod
    def _parse_place(place: object) -> PlaceSearchCandidateRead:
        if not isinstance(place, dict):
            raise TypeError
        place_data = cast("dict[str, object]", place)
        display_name = place_data.get("displayName")
        location = place_data.get("location")
        if not isinstance(display_name, dict) or not isinstance(location, dict):
            raise TypeError
        display_name_data = cast("dict[str, object]", display_name)
        location_data = cast("dict[str, object]", location)
        provider_place_id = place_data.get("id")
        name = display_name_data.get("text")
        formatted_address = place_data.get("formattedAddress")
        latitude = location_data.get("latitude")
        longitude = location_data.get("longitude")
        if (
            not isinstance(provider_place_id, str)
            or not isinstance(name, str)
            or not isinstance(formatted_address, str)
            or isinstance(latitude, bool)
            or not isinstance(latitude, (int, float))
            or isinstance(longitude, bool)
            or not isinstance(longitude, (int, float))
        ):
            raise TypeError
        return PlaceSearchCandidateRead(
            provider_place_id=provider_place_id,
            name=name,
            formatted_address=formatted_address,
            latitude=latitude,
            longitude=longitude,
        )
