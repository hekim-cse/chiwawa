# Google Places 일반 장소 검색 Provider 계약 테스트
from __future__ import annotations

import json
from typing import cast

import httpx
import pytest
from pydantic import SecretStr

from chiwawa_backend.config import Settings
from chiwawa_backend.errors import UpstreamServiceError
from chiwawa_backend.services.google_place_search import GooglePlaceSearchProvider


def _settings() -> Settings:
    return Settings(
        google_maps_api_key=SecretStr("test-key"),
        place_search_page_size=5,
    )


@pytest.mark.anyio
async def test_search_uses_korean_japan_contract_and_parses_places() -> None:
    received_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        received_requests.append(request)
        return httpx.Response(
            200,
            json={
                "places": [
                    {
                        "id": "google-tokyo-station",
                        "displayName": {"text": "도쿄역"},
                        "formattedAddress": "일본 도쿄도 지요다구",
                        "location": {
                            "latitude": 35.6812,
                            "longitude": 139.7671,
                        },
                    },
                ],
            },
        )

    provider = GooglePlaceSearchProvider(
        _settings(),
        transport=httpx.MockTransport(handler),
    )
    result = await provider.search(query="도쿄역", city_bias="Tokyo")

    assert len(received_requests) == 1
    received_request = received_requests[0]
    body = cast("dict[str, object]", json.loads(received_request.content))
    assert body == {
        "textQuery": "도쿄역 Tokyo",
        "pageSize": 5,
        "languageCode": "ko",
    }
    assert received_request.headers["X-Goog-Api-Key"] == "test-key"
    assert result[0].provider_place_id == "google-tokyo-station"
    assert result[0].name == "도쿄역"


@pytest.mark.anyio
async def test_search_returns_empty_tuple_for_empty_google_result() -> None:
    provider = GooglePlaceSearchProvider(
        _settings(),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={}),
        ),
    )

    assert await provider.search(query="없는 장소", city_bias=None) == ()


@pytest.mark.anyio
async def test_search_rejects_invalid_place_instead_of_silently_skipping() -> None:
    provider = GooglePlaceSearchProvider(
        _settings(),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"places": [{"id": "missing-fields"}]},
            ),
        ),
    )

    with pytest.raises(UpstreamServiceError, match="응답 계약"):
        _ = await provider.search(query="도쿄", city_bias=None)


@pytest.mark.anyio
async def test_search_maps_http_error_without_exposing_body() -> None:
    provider = GooglePlaceSearchProvider(
        _settings(),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, text="sensitive-body"),
        ),
    )

    with pytest.raises(UpstreamServiceError) as error_info:
        _ = await provider.search(query="도쿄", city_bias=None)
    assert "HTTP 429" in str(error_info.value)
    assert "sensitive-body" not in str(error_info.value)
