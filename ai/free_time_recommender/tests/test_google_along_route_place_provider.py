# Google Places 경로 주변 장소 Provider 계약 테스트
import json
from typing import Callable

import httpx
import pytest

from ai.free_time_recommender.domain.place_candidate import (
    AlongRoutePlaceSearchQuery,
    RecommendationCategory,
)
from ai.free_time_recommender.providers.errors import (
    AlongRoutePlaceHttpError,
    AlongRoutePlaceTimeoutError,
    AlongRoutePlaceTransportError,
    InvalidAlongRoutePlaceResponseError,
)
from ai.free_time_recommender.providers.google_along_route_place_provider import (
    GoogleAlongRoutePlaceProvider,
)


# MockTransport가 적용된 Provider 생성 헬퍼
def make_provider(
    handler: Callable[[httpx.Request], httpx.Response],
) -> GoogleAlongRoutePlaceProvider:
    return GoogleAlongRoutePlaceProvider(
        api_key="test-api-key",
        timeout_seconds=3.0,
        transport=httpx.MockTransport(handler),
    )


# 카테고리별 경로 검색 조건 생성 헬퍼
def make_query(
    category: RecommendationCategory = RecommendationCategory.CAFE,
) -> AlongRoutePlaceSearchQuery:
    return AlongRoutePlaceSearchQuery(
        encoded_polyline="encoded-route",
        category=category,
        page_size=4,
        language_code="ko",
        region_code="JP",
    )


# Google 요청 계약과 내부 장소 후보 변환 검증
def test_search_along_route_sends_expected_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers["X-Goog-Api-Key"]
        captured["field_mask"] = request.headers["X-Goog-FieldMask"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "places": [
                    {
                        "id": "place-1",
                        "displayName": {
                            "text": "도쿄역 카페",
                            "languageCode": "ko",
                        },
                        "formattedAddress": "일본 도쿄도 지요다구",
                        "location": {
                            "latitude": 35.6812,
                            "longitude": 139.7671,
                        },
                        "rating": 4.6,
                        "userRatingCount": 123,
                    }
                ]
            },
        )

    result = make_provider(handler).search_along_route(make_query())

    assert captured["url"] == (
        "https://places.googleapis.com/v1/places:searchText"
    )
    assert captured["api_key"] == "test-api-key"
    assert captured["field_mask"] == (
        "places.id,places.displayName,places.formattedAddress,"
        "places.location,places.rating,places.userRatingCount"
    )
    assert captured["payload"] == {
        "textQuery": "카페",
        "pageSize": 4,
        "languageCode": "ko",
        "regionCode": "JP",
        "searchAlongRouteParameters": {
            "polyline": {"encodedPolyline": "encoded-route"}
        },
    }
    assert len(result) == 1
    assert result[0].place_id == "place-1"
    assert result[0].name == "도쿄역 카페"
    assert result[0].category is RecommendationCategory.CAFE
    assert result[0].formatted_address == "일본 도쿄도 지요다구"
    assert result[0].rating == 4.6
    assert result[0].user_rating_count == 123


# 결과가 없는 정상 응답은 빈 후보 목록으로 처리하는지 검증
@pytest.mark.parametrize("payload", [{}, {"places": []}])
def test_search_along_route_returns_empty_tuple(
    payload: dict[str, object],
) -> None:
    result = make_provider(
        lambda request: httpx.Response(200, json=payload)
    ).search_along_route(make_query())

    assert result == ()


# HTTP 오류에서 Provider 응답 본문을 노출하지 않는지 검증
def test_search_along_route_maps_http_error() -> None:
    provider = make_provider(
        lambda request: httpx.Response(
            429,
            text="sensitive-provider-body",
        )
    )

    with pytest.raises(AlongRoutePlaceHttpError) as error_info:
        provider.search_along_route(make_query())

    assert error_info.value.status_code == 429
    assert "sensitive-provider-body" not in str(error_info.value)


# 제한시간 초과와 네트워크 오류의 개별 매핑 검증
@pytest.mark.parametrize(
    ("transport_error", "expected_exception"),
    [
        (httpx.ReadTimeout("timeout"), AlongRoutePlaceTimeoutError),
        (httpx.ConnectError("connection"), AlongRoutePlaceTransportError),
    ],
)
def test_search_along_route_maps_transport_errors(
    transport_error: httpx.TransportError,
    expected_exception: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise transport_error

    with pytest.raises(expected_exception):
        make_provider(handler).search_along_route(make_query())


# 필수값이 누락된 장소의 전체 계약 오류 처리 검증
@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"places": {}},
        {"places": [None]},
        {"places": [{}]},
        {
            "places": [
                {
                    "id": "place-1",
                    "displayName": {"text": "장소"},
                    "location": {"latitude": 35.6812},
                }
            ]
        },
    ],
)
def test_search_along_route_rejects_invalid_response(payload: object) -> None:
    with pytest.raises(InvalidAlongRoutePlaceResponseError):
        make_provider(
            lambda request: httpx.Response(200, json=payload)
        ).search_along_route(make_query())


# 모든 내부 카테고리가 명시적인 Google 검색어를 갖는지 검증
def test_all_categories_have_explicit_google_search_text() -> None:
    assert GoogleAlongRoutePlaceProvider.CATEGORY_SEARCH_TEXT == {
        RecommendationCategory.LANDMARK: "랜드마크 관광명소",
        RecommendationCategory.CAFE: "카페",
        RecommendationCategory.CULTURE: "박물관 미술관 전시관",
        RecommendationCategory.PARK: "공원 정원",
        RecommendationCategory.RESTAURANT: "음식점",
    }
