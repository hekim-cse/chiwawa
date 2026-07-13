# TripPlannerService 단위 및 전체 흐름 테스트
from ai.route_planner.domain.schemas import (
    TravelMode,
    TravelTimeElement,
    TravelTimeMatrixResult,
)
from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
    TripPlanningResponseDTO,
)
from ai.route_planner.services.trip_planner_service import (
    TripPlannerService,
)
from ai.route_planner.tests.test_route_option_solver import (
    make_request_payload,
)


# 모든 이동 방식의 Matrix를 정상 반환하는 Fake Provider
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

        matrix = {
            (origin, destination): (
                travel_minutes_by_mode[travel_mode]
            )
            for origin in place_ids
            for destination in place_ids
            if origin != destination
        }

        return TravelTimeMatrixResult(
            matrix=matrix,
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


# 전체 일정 생성 결과가 DTO 형태로 반환되는지 검증
def test_plan_trip_returns_response_with_route_options_and_timelines():
    request = TripPlanningRequestDTO.model_validate(
        make_request_payload()
    )
    service = TripPlannerService(
        routes_provider=FakeRoutesProvider()
    )

    response = service.plan_trip(
        request
    )

    assert isinstance(
        response,
        TripPlanningResponseDTO,
    )

    route_options = response.day_plans[0].route_options

    assert [
        route_option.travel_mode
        for route_option in route_options
    ] == [
        TravelMode.DRIVE,
        TravelMode.WALK,
        TravelMode.TRANSIT,
    ]

    assert all(
        route_option.timeline is not None
        for route_option in route_options
    )


# TRANSIT 누락 시 해당 Timeline만 생략하는지 검증
def test_plan_trip_preserves_other_modes_when_transit_is_missing():
    request = TripPlanningRequestDTO.model_validate(
        make_request_payload()
    )
    service = TripPlannerService(
        routes_provider=(
            FakeRoutesProviderWithTransitMissing()
        )
    )

    response = service.plan_trip(
        request
    )

    route_options_by_mode = {
        route_option.travel_mode: route_option
        for route_option
        in response.day_plans[0].route_options
    }

    assert (
        route_options_by_mode[
            TravelMode.DRIVE
        ].timeline
        is not None
    )
    assert (
        route_options_by_mode[
            TravelMode.WALK
        ].timeline
        is not None
    )

    transit_option = route_options_by_mode[
        TravelMode.TRANSIT
    ]

    assert transit_option.timeline is None
    assert transit_option.missing_segments
    assert any(
        "시간표를 생성하지 않았습니다" in warning
        for warning in transit_option.warnings
    )


# Service가 각 이동 방식별 Provider 호출을 수행하는지 검증
def test_plan_trip_calls_provider_for_each_travel_mode():
    request = TripPlanningRequestDTO.model_validate(
        make_request_payload()
    )

    class RecordingRoutesProvider:
        def __init__(self):
            self.called_modes = []

        def build_travel_time_matrix_result(
            self,
            locations,
            travel_mode,
        ) -> TravelTimeMatrixResult:
            self.called_modes.append(
                travel_mode
            )

            place_ids = [
                location.name
                for location in locations
            ]

            return TravelTimeMatrixResult(
                matrix={
                    (origin, destination): 10
                    for origin in place_ids
                    for destination in place_ids
                    if origin != destination
                },
                missing_elements=[],
            )

    provider = RecordingRoutesProvider()
    service = TripPlannerService(
        routes_provider=provider
    )

    service.plan_trip(
        request
    )

    assert provider.called_modes == [
        TravelMode.DRIVE,
        TravelMode.WALK,
        TravelMode.TRANSIT,
    ]
