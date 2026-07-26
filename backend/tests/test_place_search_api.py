# Flutter 일반 장소 검색 Endpoint 계약 테스트
from __future__ import annotations

from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.place_search import PlaceSearchCandidateRead


class CapturingPlaceSearchProvider:
    def __init__(self) -> None:
        self.query: str | None = None
        self.city_bias: str | None = None

    async def search(
        self,
        *,
        query: str,
        city_bias: str | None,
    ) -> tuple[PlaceSearchCandidateRead, ...]:
        self.query = query
        self.city_bias = city_bias
        return (
            PlaceSearchCandidateRead(
                provider_place_id="google-tokyo-station",
                name="도쿄역",
                formatted_address="일본 도쿄도 지요다구",
                latitude=35.6812,
                longitude=139.7671,
            ),
        )


@pytest.mark.anyio
async def test_place_search_endpoint_preserves_frontend_contract() -> None:
    provider = CapturingPlaceSearchProvider()
    app = create_app(place_search_provider=provider)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/places/search",
            params={"query": " 도쿄역 ", "city_bias": " Tokyo "},
        )

    assert response.status_code == HTTPStatus.OK
    assert provider.query == "도쿄역"
    assert provider.city_bias == "Tokyo"
    assert response.json()["items"][0] == {
        "provider_place_id": "google-tokyo-station",
        "name": "도쿄역",
        "formatted_address": "일본 도쿄도 지요다구",
        "latitude": 35.6812,
        "longitude": 139.7671,
    }


@pytest.mark.anyio
async def test_place_search_endpoint_rejects_blank_query() -> None:
    provider = CapturingPlaceSearchProvider()
    app = create_app(place_search_provider=provider)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/places/search",
            params={"query": "   "},
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert provider.query is None
