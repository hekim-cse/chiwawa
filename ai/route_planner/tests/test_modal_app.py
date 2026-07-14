# Modal entrypoint의 요청 검증과 TripPlannerService 연결 테스트
import pytest
from pydantic import ValidationError

from ai.route_planner.domain.schemas import (
    TravelMode,
    TravelTimeElement,
    TravelTimeMatrixResult,
)
from ai.route_planner.modal_app import (
    plan_trip_payload,
)
from ai.route_planner.tests.test_route_option_solver import (
    make_request_payload,
)


# 모든 이동 방식에 정상 Matrix를 반환하는 Fake Provider
class FakeRoutesProvider:
    def build_travel_time_matrix_result(
        self,
        locations,
        travel_mode,
    ) -> TravelTimeMatrixResult:
        place_ids = [
            location.name
            for location in locations
        ]

        travel_minutes_by_mode = {
            TravelMode.DRIVE: 10,
            TravelMode.WALK: 20,
            TravelMode.TRANSIT: 15,
        }

        return TravelTimeMatrixResult(
            matrix={
                (origin, destination): (
                    travel_minutes_by_mode[travel_mode]
                )
                for origin in place_ids
                for destination in place_ids
                if origin != destination
            },
            missing_elements=[],
        )


# TRANSIT에 누락 구간을 반환하는 Fake Provider
class FakeRoutesProviderWithTransitMissing:
    def build_travel_time_matrix_result(
        self,
        locations,
        travel_mode,
    ) -> TravelTimeMatrixResult:
        place_ids = [
            location.name
            for location in locations
        ]

        missing_elements = []

        if travel_mode == TravelMode.TRANSIT:
            missing_elements = [
                TravelTimeElement(
                    origin_name=place_ids[0],
                    destination_name=place_ids[1],
                    origin_index=0,
                    destination_index=1,
                    duration_seconds=None,
                    condition="ROUTE_NOT_FOUND",
                )
            ]

        return TravelTimeMatrixResult(
            matrix={
                (origin, destination): 10
                for origin in place_ids
                for destination in place_ids
                if origin != destination
            },
            missing_elements=missing_elements,
        )


# 정상 payload가 전체 여행 일정 응답으로 변환되는지 검증
def test_plan_trip_payload_returns_complete_response():
    request_payload = make_request_payload()

    response_payload = plan_trip_payload(
        payload=request_payload,
        routes_provider=FakeRoutesProvider(),
    )

    # 응답의 Trip ID가 요청 payload의 Trip ID와 동일한지 검증
    assert (
        response_payload["trip_id"]
        == request_payload["trip_id"]
    )

    route_options = (
        response_payload["day_plans"][0]["route_options"]
    )

    # 모든 이동 방식이 포함되어 있는지 검증
    assert [
        route_option["travel_mode"]
        for route_option in route_options
    ] == [
        "DRIVE",
        "WALK",
        "TRANSIT",
    ]

    # 모든 이동 방식에 Timeline이 존재하는지 검증
    assert all(
        route_option["timeline"] is not None
        for route_option in route_options
    )


# TRANSIT 누락 시 해당 Timeline만 생략하는지 검증
def test_plan_trip_payload_preserves_complete_modes():
    request_payload = make_request_payload()
    response_payload = plan_trip_payload(
        payload=request_payload,
        routes_provider=(
            FakeRoutesProviderWithTransitMissing()
        ),
    )

    route_options_by_mode = {
        route_option["travel_mode"]: route_option
        for route_option
        in response_payload["day_plans"][0]["route_options"]
    }

    assert (
        route_options_by_mode["DRIVE"]["timeline"]
        is not None
    )
    assert (
        route_options_by_mode["WALK"]["timeline"]
        is not None
    )

    transit_option = route_options_by_mode["TRANSIT"]

    assert transit_option["timeline"] is None
    assert transit_option["missing_segments"]


# 잘못된 요청 payload는 Pydantic ValidationError를 발생시키는지 검증
def test_plan_trip_payload_rejects_invalid_request():
    invalid_payload = make_request_payload()
    invalid_payload["days"] = []

    with pytest.raises(
        ValidationError,
    ):
        plan_trip_payload(
            payload=invalid_payload,
            routes_provider=FakeRoutesProvider(),
        )
