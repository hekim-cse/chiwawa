# Google Routes Matrix 운영 Provider 계약 테스트
from datetime import datetime
import json
from zoneinfo import ZoneInfo

import httpx
import pytest

from ai.route_planner.domain.schemas import Location, TravelMode
from ai.route_planner.providers.errors import (
    GoogleRoutesHttpError,
    GoogleRoutesTimeoutError,
    GoogleRoutesTransportError,
    InvalidGoogleRoutesResponseError,
)
from ai.route_planner.providers.google_routes_provider import (
    GoogleRoutesProvider,
)


def make_locations(count: int = 2) -> list[Location]:
    """서로 다른 일본 좌표의 장소 목록을 생성한다."""

    return [
        Location(
            name=f"tokyo-place-{index}",
            lat=35.68 + index * 0.001,
            lng=139.76 + index * 0.001,
        )
        for index in range(count)
    ]


def make_complete_elements(
    count: int = 2,
) -> list[dict[str, object]]:
    """모든 출발·도착 조합의 Matrix 응답을 생성한다."""

    return [
        {
            "originIndex": origin_index,
            "destinationIndex": destination_index,
            "duration": (
                "0s"
                if origin_index == destination_index
                else "61s"
            ),
            "distanceMeters": (
                0 if origin_index == destination_index else 1000
            ),
            "status": {},
            "condition": "ROUTE_EXISTS",
        }
        for origin_index in range(count)
        for destination_index in range(count)
    ]


def make_provider(
    handler,
) -> GoogleRoutesProvider:
    return GoogleRoutesProvider(
        api_key="test-api-key",
        transport=httpx.MockTransport(handler),
    )


def test_build_matrix_uses_complete_google_response_and_ceil_minutes() -> None:
    """실제 초보다 짧아지지 않게 분 단위로 올림한다."""

    elements = make_complete_elements()
    elements[2].pop("duration")
    elements[2]["condition"] = "ROUTE_NOT_FOUND"
    provider = make_provider(
        lambda request: httpx.Response(200, json=elements)
    )

    result = provider.build_travel_time_matrix_result(
        locations=make_locations(),
        travel_mode=TravelMode.WALK,
    )

    assert result.matrix == {("tokyo-place-0", "tokyo-place-1"): 2}
    assert len(result.missing_elements) == 1
    assert result.missing_elements[0].origin_name == "tokyo-place-1"
    assert result.missing_elements[0].destination_name == "tokyo-place-0"


@pytest.mark.parametrize(
    ("travel_mode", "expected_routing_preference", "expects_departure"),
    [
        (TravelMode.DRIVE, "TRAFFIC_AWARE", True),
        (TravelMode.TRANSIT, None, True),
        (TravelMode.WALK, None, False),
    ],
)
def test_compute_matrix_builds_mode_specific_google_request(
    travel_mode: TravelMode,
    expected_routing_preference: str | None,
    expects_departure: bool,
) -> None:
    """이동수단별 Google Routes 요청 필드 조합을 검증한다."""

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers["X-Goog-Api-Key"]
        captured["field_mask"] = request.headers["X-Goog-FieldMask"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=make_complete_elements())

    departure_time = datetime(
        2026,
        8,
        1,
        10,
        tzinfo=ZoneInfo("Asia/Tokyo"),
    )
    make_provider(handler).compute_route_matrix(
        locations=make_locations(),
        travel_mode=travel_mode,
        departure_time=departure_time,
    )

    payload = captured["payload"]
    assert captured["url"] == GoogleRoutesProvider.BASE_URL
    assert captured["api_key"] == "test-api-key"
    assert captured["field_mask"] == GoogleRoutesProvider.FIELD_MASK
    assert payload["travelMode"] == travel_mode.value
    assert payload.get("routingPreference") == expected_routing_preference
    assert ("departureTime" in payload) is expects_departure
    if expects_departure:
        assert payload["departureTime"] == "2026-08-01T01:00:00Z"


def test_compute_matrix_applies_transit_element_limit_before_request() -> None:
    """TRANSIT의 100 elements 제한을 외부 호출 전에 적용한다."""

    provider = make_provider(
        lambda request: pytest.fail("Google API를 호출하면 안 됩니다.")
    )

    with pytest.raises(ValueError, match="maximum_elements=100"):
        provider.compute_route_matrix(
            locations=make_locations(11),
            travel_mode=TravelMode.TRANSIT,
        )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not-json"),
        httpx.Response(200, json={}),
        httpx.Response(200, json=make_complete_elements()[:-1]),
        httpx.Response(
            200,
            json=[
                *make_complete_elements(),
                make_complete_elements()[0],
            ],
        ),
        httpx.Response(
            200,
            json=[
                {
                    **element,
                    "originIndex": 99,
                }
                if index == 0
                else element
                for index, element in enumerate(make_complete_elements())
            ],
        ),
    ],
)
def test_compute_matrix_rejects_invalid_google_response(
    response: httpx.Response,
) -> None:
    provider = make_provider(lambda request: response)

    with pytest.raises(InvalidGoogleRoutesResponseError):
        provider.compute_route_matrix(
            locations=make_locations(),
            travel_mode=TravelMode.WALK,
        )


@pytest.mark.parametrize(
    ("transport_error", "expected_error"),
    [
        (httpx.ReadTimeout("timeout"), GoogleRoutesTimeoutError),
        (httpx.ConnectError("network"), GoogleRoutesTransportError),
    ],
)
def test_compute_matrix_maps_transport_errors(
    transport_error: httpx.TransportError,
    expected_error: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise transport_error

    with pytest.raises(expected_error):
        make_provider(handler).compute_route_matrix(
            locations=make_locations(),
            travel_mode=TravelMode.WALK,
        )


def test_compute_matrix_maps_http_error_without_response_body() -> None:
    provider = make_provider(
        lambda request: httpx.Response(429, text="sensitive-provider-body")
    )

    with pytest.raises(GoogleRoutesHttpError) as error_info:
        provider.compute_route_matrix(
            locations=make_locations(),
            travel_mode=TravelMode.WALK,
        )

    assert error_info.value.status_code == 429
    assert "sensitive-provider-body" not in str(error_info.value)


@pytest.mark.parametrize(
    ("api_key", "timeout", "expected_error"),
    [
        ("", 20, ValueError),
        ("key", 0, ValueError),
        ("key", float("inf"), ValueError),
        ("key", True, TypeError),
    ],
)
def test_provider_rejects_invalid_configuration(
    api_key: str,
    timeout: float,
    expected_error: type[Exception],
) -> None:
    with pytest.raises(expected_error):
        GoogleRoutesProvider(
            api_key=api_key,
            timeout_seconds=timeout,
        )
