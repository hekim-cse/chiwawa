# Google Routes 추천 후보 경유 이동 지표 Provider 계약 테스트
from datetime import datetime, timezone
import json

import httpx
import pytest

from ai.free_time_recommender.domain.candidate_route_metrics import (
    CandidateRouteMetricsQuery,
)
from ai.free_time_recommender.domain.route_geometry import RouteTravelMode
from ai.free_time_recommender.providers.errors import (
    CandidateRouteMetricsHttpError,
    CandidateRouteMetricsTimeoutError,
    CandidateRouteMetricsTransportError,
    InvalidCandidateRouteMetricsResponseError,
)
from ai.free_time_recommender.providers.google_candidate_route_metrics_provider import (
    GoogleCandidateRouteMetricsProvider,
)


def make_query() -> CandidateRouteMetricsQuery:
    return CandidateRouteMetricsQuery(
        previous_place_id="도쿄역-place-id",
        candidate_place_id="도쿄타워-place-id",
        next_place_id="시부야역-place-id",
        previous_departure_at=datetime(2026, 8, 1, 10, tzinfo=timezone.utc),
        stay_minutes=60,
        travel_mode=RouteTravelMode.TRANSIT,
    )


def test_get_metrics_requests_two_time_ordered_routes() -> None:
    requests: list[dict[str, object]] = []
    request_urls: list[str] = []
    request_headers: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        request_urls.append(str(request.url))
        request_headers.append(request.headers)
        duration = "601s" if len(requests) == 1 else "300s"
        distance = 1200 if len(requests) == 1 else 800
        return httpx.Response(
            200,
            json={
                "routes": [
                    {"legs": [{"duration": duration, "distanceMeters": distance}]}
                ]
            },
        )

    provider = GoogleCandidateRouteMetricsProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    result = provider.get_candidate_route_metrics(make_query())

    assert request_urls == [
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        "https://routes.googleapis.com/directions/v2:computeRoutes",
    ]
    assert all(
        headers["X-Goog-Api-Key"] == "test-key"
        for headers in request_headers
    )
    assert all(
        headers["X-Goog-FieldMask"]
        == "routes.legs.duration,routes.legs.distanceMeters"
        for headers in request_headers
    )
    assert requests[0]["origin"] == {"placeId": "도쿄역-place-id"}
    assert requests[0]["destination"] == {"placeId": "도쿄타워-place-id"}
    assert requests[0]["languageCode"] == "ko"
    assert requests[0]["regionCode"] == "JP"
    assert requests[0]["travelMode"] == "TRANSIT"
    assert requests[0]["departureTime"] == "2026-08-01T10:00:00Z"
    assert requests[1]["origin"] == {"placeId": "도쿄타워-place-id"}
    assert requests[1]["destination"] == {"placeId": "시부야역-place-id"}
    assert requests[1]["departureTime"] == "2026-08-01T11:11:00Z"
    assert result.previous_to_candidate.travel_minutes == 11
    assert result.previous_to_candidate.distance_meters == 1200
    assert result.candidate_to_next.travel_minutes == 5
    assert result.next_arrival_at == datetime(
        2026, 8, 1, 11, 16, tzinfo=timezone.utc
    )


def test_get_metrics_uses_traffic_aware_routing_for_drive() -> None:
    """DRIVE 출발시각과 Google의 교통량 설정을 함께 전달한다."""

    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "routes": [
                    {
                        "legs": [
                            {"duration": "300s", "distanceMeters": 800}
                        ]
                    }
                ]
            },
        )

    provider = GoogleCandidateRouteMetricsProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    query = make_query()
    provider.get_candidate_route_metrics(
        CandidateRouteMetricsQuery(
            previous_place_id=query.previous_place_id,
            candidate_place_id=query.candidate_place_id,
            next_place_id=query.next_place_id,
            previous_departure_at=query.previous_departure_at,
            stay_minutes=query.stay_minutes,
            travel_mode=RouteTravelMode.DRIVE,
        )
    )

    assert len(requests) == 2
    assert all(
        request["routingPreference"] == "TRAFFIC_AWARE"
        for request in requests
    )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not-json"),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"routes": []}),
        httpx.Response(200, json={"routes": [{"legs": []}]}),
        httpx.Response(200, json={"routes": [{"legs": [{}]}]}),
        httpx.Response(
            200,
            json={"routes": [{"legs": [{"duration": "-1s", "distanceMeters": 1}]}]},
        ),
    ],
)
def test_get_metrics_rejects_invalid_response(response: httpx.Response) -> None:
    provider = GoogleCandidateRouteMetricsProvider(
        api_key="test-key",
        transport=httpx.MockTransport(lambda request: response),
    )
    with pytest.raises(InvalidCandidateRouteMetricsResponseError):
        provider.get_candidate_route_metrics(make_query())


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (httpx.ReadTimeout("timeout"), CandidateRouteMetricsTimeoutError),
        (httpx.ConnectError("network"), CandidateRouteMetricsTransportError),
    ],
)
def test_get_metrics_maps_transport_errors(
    error: httpx.TransportError,
    expected: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    provider = GoogleCandidateRouteMetricsProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(expected):
        provider.get_candidate_route_metrics(make_query())


def test_get_metrics_maps_http_error_without_response_body() -> None:
    provider = GoogleCandidateRouteMetricsProvider(
        api_key="test-key",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, text="sensitive-body")
        ),
    )
    with pytest.raises(CandidateRouteMetricsHttpError) as error_info:
        provider.get_candidate_route_metrics(make_query())
    assert "sensitive-body" not in str(error_info.value)
