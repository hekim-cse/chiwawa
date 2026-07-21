# providers/places_provider.py 테스트
# httpx MockTransport 로 실제 네트워크 없이 요청 생성·응답 파싱을 진짜 httpx 로 검증
import json

import httpx
import pytest

from ai.image_search.domain.schemas import PlaceCategory
from ai.image_search.providers.places_provider import (
    CATEGORY_INCLUDED_TYPES,
    PlacesProvider,
)


# 주어진 핸들러로 MockTransport 를 붙인 PlacesProvider 를 만든다
def make_provider(handler) -> PlacesProvider:
    return PlacesProvider(api_key="test-key", transport=httpx.MockTransport(handler))


class TestCategoryMapping:
    # 모든 PlaceCategory 가 근처 검색 타입 매핑을 갖는다
    # (미매핑 카테고리는 필터 없이 검색되는 조용한 저하로 이어지므로 전수 보장)
    def test_mapping_covers_all_place_categories(self):
        assert set(CATEGORY_INCLUDED_TYPES) == set(PlaceCategory)


class TestResolvePlace:
    # 장소명을 좌표/메타 정보로 변환한다 (요청·응답 파싱 모두 검증)
    def test_resolves_place_name_to_coordinates(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["api_key"] = request.headers.get("X-Goog-Api-Key")
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "places": [
                        {
                            "id": "place-123",
                            "displayName": {"text": "센소지"},
                            "formattedAddress": "도쿄도 다이토구 아사쿠사",
                            "location": {"latitude": 35.7148, "longitude": 139.7967},
                            "rating": 4.5,
                        }
                    ]
                },
            )

        provider = make_provider(handler)
        place = provider.resolve_place("센소지")

        # 응답 파싱 검증
        assert place.place_id == "place-123"
        assert place.name == "센소지"
        assert place.latitude == 35.7148
        assert place.longitude == 139.7967
        assert place.rating == 4.5
        assert place.formatted_address == "도쿄도 다이토구 아사쿠사"
        # 요청 생성 검증
        assert captured["path"].endswith("/v1/places:searchText")
        assert captured["api_key"] == "test-key"
        assert captured["body"]["textQuery"] == "센소지"

    # 검색 결과가 없으면 ValueError 를 던진다
    def test_raises_when_no_result(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"places": []})

        provider = make_provider(handler)
        with pytest.raises(ValueError):
            provider.resolve_place("존재하지 않는 장소")

    # HTTP 오류(4xx/5xx)면 RuntimeError 를 던진다
    def test_raises_on_http_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"error": "PERMISSION_DENIED"})

        provider = make_provider(handler)
        with pytest.raises(RuntimeError):
            provider.resolve_place("센소지")

    # 필수 필드(좌표)가 빠진 응답이면 ValueError 를 던진다
    def test_raises_on_invalid_place_shape(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"places": [{"id": "x", "displayName": {"text": "이름만"}}]},
            )

        provider = make_provider(handler)
        with pytest.raises(ValueError):
            provider.resolve_place("좌표 없는 곳")


# 하나의 완전한 Google 응답 place dict 를 만드는 헬퍼
def google_place(**overrides) -> dict:
    place = {
        "id": "place-1",
        "displayName": {"text": "센소지"},
        "formattedAddress": "일본 도쿄도 다이토구",
        "location": {"latitude": 35.7148, "longitude": 139.7967},
        "rating": 4.5,
        "userRatingCount": 138000,
        "primaryType": "buddhist_temple",
        "addressComponents": [
            {"longText": "다이토구", "types": ["locality", "political"]},
            {"longText": "도쿄도", "types": ["administrative_area_level_1", "political"]},
            {"longText": "일본", "types": ["country", "political"]},
        ],
    }
    place.update(overrides)
    return place


class TestEnrichedParsing:
    # addressComponents 에서 도시(locality)/국가(country)를 구조화 파싱한다
    def test_parses_city_and_country_from_address_components(self):
        def handler(request: httpx.Request) -> httpx.Response:
            captured_mask.append(request.headers.get("X-Goog-FieldMask", ""))
            return httpx.Response(200, json={"places": [google_place()]})

        captured_mask: list = []
        provider = make_provider(handler)
        place = provider.resolve_place("센소지")

        assert place.city == "다이토구"  # locality 우선
        assert place.country == "일본"
        # FieldMask 에 addressComponents 가 포함되어야 실제 응답에 실려 온다
        assert "places.addressComponents" in captured_mask[0]

    # locality 가 없으면 administrative_area_level_1 로 폴백한다
    def test_falls_back_to_admin_area_when_no_locality(self):
        components = [
            {"longText": "도쿄도", "types": ["administrative_area_level_1", "political"]},
            {"longText": "일본", "types": ["country", "political"]},
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"places": [google_place(addressComponents=components)]}
            )

        provider = make_provider(handler)
        place = provider.resolve_place("센소지")

        assert place.city == "도쿄도"

    # 리뷰 수와 장소 유형(primaryType)을 파싱한다
    def test_parses_review_count_and_primary_type(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"places": [google_place()]})

        provider = make_provider(handler)
        place = provider.resolve_place("센소지")

        assert place.review_count == 138000
        assert place.primary_type == "buddhist_temple"

    # addressComponents 가 아예 없으면 city/country 는 None 이다 (거부 아님)
    def test_missing_address_components_yield_none(self):
        def handler(request: httpx.Request) -> httpx.Response:
            place = google_place()
            del place["addressComponents"]
            return httpx.Response(200, json={"places": [place]})

        provider = make_provider(handler)
        place = provider.resolve_place("센소지")

        assert place.city is None
        assert place.country is None


class TestSearchNearby:
    # 좌표+카테고리로 근처 장소를 검색한다 (요청 형태·응답 파싱 모두 검증)
    def test_searches_nearby_with_category_filter(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "places": [
                        google_place(id="n1", displayName={"text": "근처 카페 1"}),
                        google_place(id="n2", displayName={"text": "근처 카페 2"}),
                    ]
                },
            )

        provider = make_provider(handler)
        results = provider.search_nearby(
            latitude=35.7148,
            longitude=139.7967,
            category=PlaceCategory.CAFE,
            radius_m=1500,
            max_result_count=4,
        )

        # 응답 파싱 검증
        assert [p.name for p in results] == ["근처 카페 1", "근처 카페 2"]
        assert results[0].city == "다이토구"  # 근처 결과도 도시/국가 파싱
        # 요청 생성 검증
        assert captured["path"].endswith("/v1/places:searchNearby")
        circle = captured["body"]["locationRestriction"]["circle"]
        assert circle["center"] == {"latitude": 35.7148, "longitude": 139.7967}
        assert circle["radius"] == 1500
        assert captured["body"]["maxResultCount"] == 4
        assert "cafe" in captured["body"]["includedTypes"]

    # 카테고리가 없으면(또는 매핑이 없으면) includedTypes 를 보내지 않는다
    def test_omits_included_types_without_category(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"places": []})

        provider = make_provider(handler)
        provider.search_nearby(latitude=35.0, longitude=139.0, category=None)

        assert "includedTypes" not in captured["body"]

    # 근처 결과가 없으면 빈 리스트를 반환한다 (resolve 와 달리 예외 아님)
    def test_returns_empty_list_when_no_results(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        provider = make_provider(handler)
        results = provider.search_nearby(latitude=35.0, longitude=139.0)

        assert results == []

    # HTTP 오류면 RuntimeError 를 던진다
    def test_raises_on_http_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "INTERNAL"})

        provider = make_provider(handler)
        with pytest.raises(RuntimeError):
            provider.search_nearby(latitude=35.0, longitude=139.0)
