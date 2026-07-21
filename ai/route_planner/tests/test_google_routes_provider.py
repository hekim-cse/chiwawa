# GoogleRoutesProvider 단위 테스트
from ai.route_planner.domain.schemas import Location, TravelTimeElement, TravelMode
from ai.route_planner.providers.google_routes_provider import GoogleRoutesProvider


# 자기 자신으로 이동하는 self-pair 구간은 missing_elements에 포함하지 않는지 검증
def test_build_travel_time_matrix_result_skips_self_pair_elements():
    provider = GoogleRoutesProvider(api_key="test-api-key")

    elements = [
        TravelTimeElement(
            origin_name="a",
            destination_name="a",
            origin_index=0,
            destination_index=0,
            duration_seconds=None,
            condition="ROUTE_NOT_FOUND",
        ),
        TravelTimeElement(
            origin_name="a",
            destination_name="b",
            origin_index=0,
            destination_index=1,
            duration_seconds=600,
            condition="ROUTE_EXISTS",
        ),
        TravelTimeElement(
            origin_name="b",
            destination_name="a",
            origin_index=1,
            destination_index=0,
            duration_seconds=None,
            condition="ROUTE_NOT_FOUND",
        ),
    ]

    provider.compute_route_matrix = (
        lambda locations, travel_mode, departure_time=None: elements
    )

    result = provider.build_travel_time_matrix_result(
        locations=[
            Location(name="a", lat=0, lng=0),
            Location(name="b", lat=1, lng=1),
        ],
        travel_mode=TravelMode.DRIVE,
    )

    assert result.matrix == {
        ("a", "b"): 10,
    }
    assert len(result.missing_elements) == 1
    assert result.missing_elements[0].origin_name == "b"
    assert result.missing_elements[0].destination_name == "a"


# TRANSIT 요청에 명시적인 UTC departureTime 전달
def test_compute_route_matrix_sends_transit_departure_time(
    monkeypatch,
):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    captured_payload = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return []

    class FakeClient:
        def __init__(
            self,
            timeout,
        ):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return None

        def post(
            self,
            url,
            headers,
            json,
        ):
            captured_payload.update(
                json
            )
            return FakeResponse()

    monkeypatch.setattr(
        "ai.route_planner.providers."
        "google_routes_provider.httpx.Client",
        FakeClient,
    )

    provider = GoogleRoutesProvider(
        api_key="test-api-key"
    )

    provider.compute_route_matrix(
        locations=[
            Location(
                name="start",
                lat=35.0,
                lng=139.0,
            ),
            Location(
                name="end",
                lat=35.1,
                lng=139.1,
            ),
        ],
        travel_mode=TravelMode.TRANSIT,
        departure_time=datetime(
            2026,
            8,
            1,
            10,
            0,
            tzinfo=ZoneInfo(
                "Asia/Tokyo"
            ),
        ),
    )

    assert (
        captured_payload[
            "departureTime"
        ]
        == "2026-08-01T01:00:00Z"
    )


# DRIVE 요청에는 departureTime을 전달하지 않음
def test_compute_route_matrix_omits_drive_departure_time(
    monkeypatch,
):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    captured_payload = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return []

    class FakeClient:
        def __init__(
            self,
            timeout,
        ):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return None

        def post(
            self,
            url,
            headers,
            json,
        ):
            captured_payload.update(
                json
            )
            return FakeResponse()

    monkeypatch.setattr(
        "ai.route_planner.providers."
        "google_routes_provider.httpx.Client",
        FakeClient,
    )

    provider = GoogleRoutesProvider(
        api_key="test-api-key"
    )

    provider.compute_route_matrix(
        locations=[
            Location(
                name="start",
                lat=35.0,
                lng=139.0,
            ),
            Location(
                name="end",
                lat=35.1,
                lng=139.1,
            ),
        ],
        travel_mode=TravelMode.DRIVE,
        departure_time=datetime(
            2026,
            8,
            1,
            10,
            0,
            tzinfo=ZoneInfo(
                "Asia/Tokyo"
            ),
        ),
    )

    assert (
        "departureTime"
        not in captured_payload
    )
