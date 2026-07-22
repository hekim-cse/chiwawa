# Google Routes 경로 geometry Provider 계약 테스트
from datetime import datetime, timedelta, timezone
import json
from typing import Callable

import httpx
import pytest

from ai.free_time_recommender.domain.route_geometry import (
    GeoCoordinate,
    RouteGeometryQuery,
    RouteTravelMode,
)
from ai.free_time_recommender.providers.errors import (
    InvalidRouteGeometryResponseError,
    RouteGeometryHttpError,
    RouteGeometryTimeoutError,
    RouteGeometryTransportError,
)
from ai.free_time_recommender.providers.google_routes_geometry_provider import (
    GoogleRoutesGeometryProvider,
)


# MockTransport가 적용된 Provider 생성 헬퍼
def make_provider(
    handler: Callable[[httpx.Request], httpx.Response],
) -> GoogleRoutesGeometryProvider:
    return GoogleRoutesGeometryProvider(
        api_key="test-api-key",
        timeout_seconds=3.0,
        transport=httpx.MockTransport(handler),
    )


# 경로 geometry 조회 조건 생성 헬퍼
def make_query(
    *,
    travel_mode: RouteTravelMode = RouteTravelMode.WALK,
    departure_at: datetime | None = None,
) -> RouteGeometryQuery:
    return RouteGeometryQuery(
        origin=GeoCoordinate(37.5665, 126.9780),
        destination=GeoCoordinate(37.5700, 126.9900),
        travel_mode=travel_mode,
        departure_at=departure_at,
    )


# Google 요청 계약과 encoded polyline 변환 검증
def test_get_route_geometry_sends_expected_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers["X-Goog-Api-Key"]
        captured["field_mask"] = request.headers[
            "X-Goog-FieldMask"
        ]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "routes": [
                    {
                        "polyline": {
                            "encodedPolyline": "encoded-route",
                        }
                    }
                ]
            },
        )

    result = make_provider(handler).get_route_geometry(make_query())

    assert captured["url"] == (
        "https://routes.googleapis.com/directions/v2:computeRoutes"
    )
    assert captured["api_key"] == "test-api-key"
    assert captured["field_mask"] == (
        "routes.polyline.encodedPolyline"
    )
    assert captured["payload"] == {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": 37.5665,
                    "longitude": 126.978,
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": 37.57,
                    "longitude": 126.99,
                }
            }
        },
        "travelMode": "WALK",
        "computeAlternativeRoutes": False,
        "polylineQuality": "OVERVIEW",
        "polylineEncoding": "ENCODED_POLYLINE",
    }
    assert result.encoded_polyline == "encoded-route"


# 출발시각을 UTC 형식으로 전달하는지 검증
def test_get_route_geometry_converts_departure_at_to_utc() -> None:
    captured_payload: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(
            json.loads(request.content)
        )
        return httpx.Response(
            200,
            json={
                "routes": [
                    {
                        "polyline": {
                            "encodedPolyline": "transit-route",
                        }
                    }
                ]
            },
        )

    departure_at = datetime(
        2026,
        8,
        1,
        10,
        tzinfo=timezone(timedelta(hours=9)),
    )
    make_provider(handler).get_route_geometry(
        make_query(
            travel_mode=RouteTravelMode.TRANSIT,
            departure_at=departure_at,
        )
    )

    assert captured_payload["departureTime"] == (
        "2026-08-01T01:00:00Z"
    )


# HTTP 오류에서 응답 본문을 노출하지 않는 명시적 오류 검증
def test_get_route_geometry_maps_http_error() -> None:
    provider = make_provider(
        lambda request: httpx.Response(
            429,
            text="sensitive-provider-body",
        )
    )

    with pytest.raises(RouteGeometryHttpError) as error_info:
        provider.get_route_geometry(make_query())

    assert error_info.value.status_code == 429
    assert "sensitive-provider-body" not in str(error_info.value)


# 제한시간 초과와 네트워크 오류의 개별 매핑 검증
@pytest.mark.parametrize(
    ("transport_error", "expected_exception"),
    [
        (httpx.ReadTimeout("timeout"), RouteGeometryTimeoutError),
        (httpx.ConnectError("connection"), RouteGeometryTransportError),
    ],
)
def test_get_route_geometry_maps_transport_errors(
    transport_error: httpx.TransportError,
    expected_exception: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise transport_error

    with pytest.raises(expected_exception):
        make_provider(handler).get_route_geometry(make_query())


# 잘못된 Google 응답 계약 거부 검증
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not-json"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"routes": []}),
        httpx.Response(200, json={"routes": [{}, {}]}),
        httpx.Response(200, json={"routes": [{}]}),
        httpx.Response(
            200,
            json={"routes": [{"polyline": {}}]},
        ),
        httpx.Response(
            200,
            json={
                "routes": [
                    {"polyline": {"encodedPolyline": " "}}
                ]
            },
        ),
    ],
)
def test_get_route_geometry_rejects_invalid_response(
    response: httpx.Response,
) -> None:
    with pytest.raises(InvalidRouteGeometryResponseError):
        make_provider(lambda request: response).get_route_geometry(
            make_query()
        )


# Provider 설정의 빈 API 키와 잘못된 timeout 거부 검증
@pytest.mark.parametrize(
    ("updates", "exception_type"),
    [
        ({"api_key": ""}, ValueError),
        ({"api_key": "   "}, ValueError),
        ({"timeout_seconds": 0}, ValueError),
        ({"timeout_seconds": -1}, ValueError),
        ({"timeout_seconds": float("nan")}, ValueError),
        ({"timeout_seconds": float("inf")}, ValueError),
        ({"timeout_seconds": True}, TypeError),
    ],
)
def test_provider_rejects_invalid_configuration(
    updates: dict[str, object],
    exception_type: type[Exception],
) -> None:
    values: dict[str, object] = {
        "api_key": "test-api-key",
        "timeout_seconds": 3.0,
    }
    values.update(updates)

    with pytest.raises(exception_type):
        GoogleRoutesGeometryProvider(**values)
