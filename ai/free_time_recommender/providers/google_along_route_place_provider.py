# Google Places Text Search를 이용한 경로 주변 장소 Provider
from __future__ import annotations

import math

import httpx

from ai.free_time_recommender.domain.place_candidate import (
    AlongRoutePlaceSearchQuery,
    PlaceCandidate,
    RecommendationCategory,
)
from ai.free_time_recommender.domain.route_geometry import GeoCoordinate
from ai.free_time_recommender.providers.errors import (
    AlongRoutePlaceHttpError,
    AlongRoutePlaceTimeoutError,
    AlongRoutePlaceTransportError,
    InvalidAlongRoutePlaceResponseError,
)


class GoogleAlongRoutePlaceProvider:
    """Google Places의 경로 편향 Text Search 구현."""

    BASE_URL = "https://places.googleapis.com/v1/places:searchText"
    FIELD_MASK = (
        "places.id,places.displayName,places.formattedAddress,"
        "places.location,places.rating,places.userRatingCount"
    )
    CATEGORY_SEARCH_TEXT = {
        RecommendationCategory.LANDMARK: "랜드마크 관광명소",
        RecommendationCategory.CAFE: "카페",
        RecommendationCategory.CULTURE: "박물관 미술관 전시관",
        RecommendationCategory.PARK: "공원 정원",
        RecommendationCategory.RESTAURANT: "음식점",
    }

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not isinstance(api_key, str):
            raise TypeError("api_key는 문자열이어야 합니다.")
        if not api_key.strip():
            raise ValueError("api_key는 비어 있을 수 없습니다.")
        if isinstance(timeout_seconds, bool) or not isinstance(
            timeout_seconds,
            (int, float),
        ):
            raise TypeError("timeout_seconds는 숫자여야 합니다.")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds는 0보다 큰 유한한 값이어야 합니다."
            )

        self._api_key = api_key
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport

    def search_along_route(
        self,
        query: AlongRoutePlaceSearchQuery,
    ) -> tuple[PlaceCandidate, ...]:
        """내부 조건을 Google 요청으로 변환하고 후보를 반환한다."""

        if not isinstance(query, AlongRoutePlaceSearchQuery):
            raise TypeError("query는 AlongRoutePlaceSearchQuery여야 합니다.")

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": self.FIELD_MASK,
        }
        payload = {
            "textQuery": self.CATEGORY_SEARCH_TEXT[query.category],
            "pageSize": query.page_size,
            "languageCode": query.language_code,
            "regionCode": query.region_code,
            "searchAlongRouteParameters": {
                "polyline": {"encodedPolyline": query.encoded_polyline}
            },
        }

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as error:
            raise AlongRoutePlaceTimeoutError(
                "Google Places API 요청 시간이 초과됐습니다."
            ) from error
        except httpx.TransportError as error:
            raise AlongRoutePlaceTransportError(
                "Google Places API 네트워크 요청에 실패했습니다."
            ) from error

        if response.status_code >= 400:
            raise AlongRoutePlaceHttpError(response.status_code)
        return self._parse_response(response, query.category)

    @classmethod
    def _parse_response(
        cls,
        response: httpx.Response,
        category: RecommendationCategory,
    ) -> tuple[PlaceCandidate, ...]:
        try:
            payload = response.json()
        except ValueError as error:
            raise InvalidAlongRoutePlaceResponseError(
                "Google Places API 응답이 JSON 형식이 아닙니다."
            ) from error
        if not isinstance(payload, dict):
            raise InvalidAlongRoutePlaceResponseError(
                "Google Places API 응답 최상위 값은 객체여야 합니다."
            )

        places = payload.get("places", [])
        if not isinstance(places, list):
            raise InvalidAlongRoutePlaceResponseError(
                "Google Places API places 값은 배열이어야 합니다."
            )

        candidates: list[PlaceCandidate] = []
        for index, place in enumerate(places):
            try:
                candidates.append(cls._parse_place(place, category))
            except (TypeError, ValueError, KeyError) as error:
                raise InvalidAlongRoutePlaceResponseError(
                    "Google Places API 장소 응답이 유효하지 않습니다. "
                    f"index={index}"
                ) from error
        return tuple(candidates)

    @staticmethod
    def _parse_place(
        place: object,
        category: RecommendationCategory,
    ) -> PlaceCandidate:
        if not isinstance(place, dict):
            raise TypeError("장소 값은 객체여야 합니다.")
        display_name = place["displayName"]
        location = place["location"]
        if not isinstance(display_name, dict):
            raise TypeError("displayName은 객체여야 합니다.")
        if not isinstance(location, dict):
            raise TypeError("location은 객체여야 합니다.")

        return PlaceCandidate(
            place_id=place["id"],
            name=display_name["text"],
            coordinate=GeoCoordinate(
                latitude=location["latitude"],
                longitude=location["longitude"],
            ),
            category=category,
            formatted_address=place.get("formattedAddress"),
            rating=place.get("rating"),
            user_rating_count=place.get("userRatingCount"),
        )
