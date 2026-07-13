# 이동 방식별 Route Option과 Timeline 전체 실행 흐름 테스트
from ai.route_planner.domain.schemas import (
    TravelMode,
    TravelTimeElement,
    TravelTimeMatrixResult,
)
from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)
from ai.route_planner.scripts.run_timeline_options import (
    run_timeline_options,
)
from ai.route_planner.tests.test_route_option_solver import (
    make_request_payload,
)


# 테스트용 정상 Google Routes Provider
class FakeGoogleRoutesProvider:
    # 이동 방식에 따라 서로 다른 이동 시간을 가진 완전한 Matrix를 반환
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

        travel_minutes = travel_minutes_by_mode[
            travel_mode
        ]

        matrix = {
            (origin, destination): travel_minutes
            for origin in place_ids
            for destination in place_ids
            if origin != destination
        }

        return TravelTimeMatrixResult(
            matrix=matrix,
            missing_elements=[],
        )


# TRANSIT에 Provider 누락 구간이 있는 테스트용 Provider
class FakeGoogleRoutesProviderWithTransitMissing:
    def build_travel_time_matrix_result(
        self,
        locations,
        travel_mode,
    ) -> TravelTimeMatrixResult:
        place_ids = [
            location.name
            for location in locations
        ]

        matrix = {
            (origin, destination): 10
            for origin in place_ids
            for destination in place_ids
            if origin != destination
        }

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
            matrix=matrix,
            missing_elements=missing_elements,
        )


# 세 이동 방식의 Route Option과 Timeline이 모두 생성되는지 검증
def test_run_timeline_options_builds_timelines_for_all_modes():
    request = TripPlanningRequestDTO.model_validate(
        make_request_payload()
    )

    response_payload = run_timeline_options(
        request=request,
        routes_provider=FakeGoogleRoutesProvider(),
    )

    route_options = (
        response_payload["day_plans"][0]["route_options"]
    )

    assert len(route_options) == 3

    assert [
        route_option["travel_mode"]
        for route_option in route_options
    ] == [
        "DRIVE",
        "WALK",
        "TRANSIT",
    ]

    assert all(
        route_option["timeline"] is not None
        for route_option in route_options
    )

    assert all(
        route_option["timeline"]["timeline_stops"]
        for route_option in route_options
    )


# TRANSIT 누락 시 해당 Timeline만 생략하고 다른 이동 방식은 유지하는지 검증
def test_run_timeline_options_skips_only_transit_with_missing_segments():
    request = TripPlanningRequestDTO.model_validate(
        make_request_payload()
    )

    response_payload = run_timeline_options(
        request=request,
        routes_provider=(
            FakeGoogleRoutesProviderWithTransitMissing()
        ),
    )

    route_options = (
        response_payload["day_plans"][0]["route_options"]
    )

    route_options_by_mode = {
        route_option["travel_mode"]: route_option
        for route_option in route_options
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
    assert any(
        "시간표를 생성하지 않았습니다" in warning
        for warning in transit_option["warnings"]
    )
