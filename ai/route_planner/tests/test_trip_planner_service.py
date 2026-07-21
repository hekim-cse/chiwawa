# TripPlannerService의 Matrix 선조회와 정확 일자 배정 이후 전체 일정 생성 흐름을 검증하는 테스트
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
    TripPlannerServiceConfig,
)
from ai.route_planner.tests.test_route_option_solver import (
    make_request_payload,
)


# 전달된 모든 장소 사이의 완전한 Matrix 생성
def make_complete_matrix_result(
    locations,
    travel_minutes: int,
) -> TravelTimeMatrixResult:
    place_ids = [
        location.name
        for location in locations
    ]

    return TravelTimeMatrixResult(
        matrix={
            (origin, destination): (
                travel_minutes
            )
            for origin in place_ids
            for destination in place_ids
            if origin != destination
        },
        missing_elements=[],
    )


# 모든 이동 방식의 완전한 Matrix를 반환하는 Fake Provider
class FakeRoutesProvider:
    def build_travel_time_matrix_result(
        self,
        locations,
        travel_mode,
        departure_time=None,
    ) -> TravelTimeMatrixResult:
        travel_minutes_by_mode = {
            TravelMode.DRIVE: 10,
            TravelMode.WALK: 20,
            TravelMode.TRANSIT: 15,
        }

        return make_complete_matrix_result(
            locations=locations,
            travel_minutes=(
                travel_minutes_by_mode[
                    travel_mode
                ]
            ),
        )


# 경로 옵션용 TRANSIT 요청에 누락 구간을 반환하는 Fake Provider
class FakeRoutesProviderWithTransitMissing:
    def __init__(self) -> None:
        self.call_count = 0

    def build_travel_time_matrix_result(
        self,
        locations,
        travel_mode,
        departure_time=None,
    ) -> TravelTimeMatrixResult:
        self.call_count += 1

        result = make_complete_matrix_result(
            locations=locations,
            travel_minutes=10,
        )

        # 첫 호출은 정확 일자 배정 DRIVE Matrix이므로
        # 이후 TRANSIT 경로 옵션 요청에만 누락 구간 추가
        if (
            self.call_count > 1
            and travel_mode
            == TravelMode.TRANSIT
        ):
            place_ids = [
                location.name
                for location in locations
            ]

            return TravelTimeMatrixResult(
                matrix=result.matrix,
                missing_elements=[
                    TravelTimeElement(
                        origin_name=place_ids[0],
                        destination_name=(
                            place_ids[1]
                        ),
                        origin_index=0,
                        destination_index=1,
                        duration_seconds=None,
                        condition=(
                            "ROUTE_NOT_FOUND"
                        ),
                    )
                ],
            )

        return result


# 명시적인 DRIVE 정확 일자 배정 설정으로 Service 생성
def make_service(
    routes_provider,
) -> TripPlannerService:
    return TripPlannerService(
        routes_provider=routes_provider,
        config=TripPlannerServiceConfig(
            day_assignment_travel_mode=(
                TravelMode.DRIVE
            ),
        ),
    )


# 정확 일자 배정과 모든 이동 방식의 Route Option 및 Timeline 생성
def test_plan_trip_returns_response_with_route_options_and_timelines():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    response = make_service(
        FakeRoutesProvider()
    ).plan_trip(request)

    assert isinstance(
        response,
        TripPlanningResponseDTO,
    )

    route_options = (
        response
        .day_plans[0]
        .route_options
    )

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


# TRANSIT 누락 시 다른 이동 방식 Timeline을 유지
def test_plan_trip_preserves_other_modes_when_transit_is_missing():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    response = make_service(
        FakeRoutesProviderWithTransitMissing()
    ).plan_trip(request)

    route_options_by_mode = {
        route_option.travel_mode: (
            route_option
        )
        for route_option
        in response
        .day_plans[0]
        .route_options
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

    transit_option = (
        route_options_by_mode[
            TravelMode.TRANSIT
        ]
    )

    assert transit_option.timeline is None
    assert transit_option.missing_segments
    assert any(
        "시간표를 생성하지 않았습니다"
        in warning
        for warning
        in transit_option.warnings
    )


# 일자 배정 Matrix를 경로 옵션 Matrix보다 먼저 조회
def test_plan_trip_fetches_assignment_matrix_before_route_matrices():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    class RecordingRoutesProvider:
        def __init__(self) -> None:
            self.calls = []

        def build_travel_time_matrix_result(
            self,
            locations,
            travel_mode,
            departure_time=None,
        ) -> TravelTimeMatrixResult:
            self.calls.append(
                (
                    travel_mode,
                    tuple(
                        location.name
                        for location in locations
                    ),
                )
            )

            return make_complete_matrix_result(
                locations=locations,
                travel_minutes=10,
            )

    provider = RecordingRoutesProvider()

    make_service(provider).plan_trip(
        request
    )

    assert [
        travel_mode
        for travel_mode, _
        in provider.calls
    ] == [
        TravelMode.DRIVE,
        TravelMode.DRIVE,
        TravelMode.WALK,
        TravelMode.TRANSIT,
    ]

    assignment_location_names = (
        provider.calls[0][1]
    )

    assert (
        request.days[0]
        .start_place.place_id
        in assignment_location_names
    )
    assert (
        request.days[0]
        .end_place.place_id
        in assignment_location_names
    )
    assert {
        poi.place_id
        for poi in request.pois
    }.issubset(
        set(assignment_location_names)
    )


# 설정된 일자 배정 이동 방식을 Provider 요청에 그대로 전달
def test_plan_trip_uses_explicit_assignment_travel_mode():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    class RecordingRoutesProvider:
        def __init__(self) -> None:
            self.called_modes = []

        def build_travel_time_matrix_result(
            self,
            locations,
            travel_mode,
            departure_time=None,
        ) -> TravelTimeMatrixResult:
            self.called_modes.append(
                travel_mode
            )

            return make_complete_matrix_result(
                locations=locations,
                travel_minutes=10,
            )

    provider = RecordingRoutesProvider()

    service = TripPlannerService(
        routes_provider=provider,
        config=TripPlannerServiceConfig(
            day_assignment_travel_mode=(
                TravelMode.WALK
            ),
        ),
    )

    service.plan_trip(request)

    assert provider.called_modes[0] == (
        TravelMode.WALK
    )


# 일자 배정 Matrix 누락 구간에 가짜 이동시간을 추가하지 않음
def test_plan_trip_preserves_missing_assignment_segments():
    payload = make_request_payload()

    # 필수 방문 POI 한 개만 사용해 완전 경로 부재를 명확히 검증
    payload["pois"] = [
        payload["pois"][0]
    ]

    request = (
        TripPlanningRequestDTO
        .model_validate(payload)
    )

    class MissingAssignmentRouteProvider:
        def __init__(self) -> None:
            self.call_count = 0

        def build_travel_time_matrix_result(
            self,
            locations,
            travel_mode,
            departure_time=None,
        ) -> TravelTimeMatrixResult:
            self.call_count += 1

            if self.call_count == 1:
                place_ids = [
                    location.name
                    for location in locations
                ]

                return TravelTimeMatrixResult(
                    matrix={
                        (
                            place_ids[0],
                            place_ids[-1],
                        ): 10,
                    },
                    missing_elements=[],
                )

            return make_complete_matrix_result(
                locations=locations,
                travel_minutes=10,
            )

    response = make_service(
        MissingAssignmentRouteProvider()
    ).plan_trip(request)

    assert (
        response
        .unassigned_pois[0]
        .poi.poi_id
        == request.pois[0].poi_id
    )


# 여행 timezone과 day 시작 시각을 Provider에 전달
def test_plan_trip_passes_timezone_aware_departure_time():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    class RecordingDepartureTimeProvider:
        def __init__(self) -> None:
            self.departure_times = []

        def build_travel_time_matrix_result(
            self,
            locations,
            travel_mode,
            departure_time=None,
        ) -> TravelTimeMatrixResult:
            self.departure_times.append(
                (
                    travel_mode,
                    departure_time,
                )
            )

            return make_complete_matrix_result(
                locations=locations,
                travel_minutes=10,
            )

    provider = (
        RecordingDepartureTimeProvider()
    )

    make_service(provider).plan_trip(
        request
    )

    assert provider.departure_times

    for (
        _,
        departure_time,
    ) in provider.departure_times:
        assert departure_time is not None
        assert (
            departure_time.utcoffset()
            is not None
        )
        assert (
            departure_time.isoformat()
            == "2026-08-01T10:00:00+09:00"
        )


# 실제 Google 응답처럼 TRANSIT 전체 구간이 누락된 Provider
class FakeRoutesProviderWithEmptyTransitMatrix:
    def __init__(self) -> None:
        self.call_count = 0

    def build_travel_time_matrix_result(
        self,
        locations,
        travel_mode,
        departure_time=None,
    ) -> TravelTimeMatrixResult:
        self.call_count += 1

        # 첫 호출은 일자 배정 Matrix
        if (
            self.call_count == 1
            or travel_mode
            != TravelMode.TRANSIT
        ):
            return make_complete_matrix_result(
                locations=locations,
                travel_minutes=10,
            )

        missing_elements = [
            TravelTimeElement(
                origin_name=origin.name,
                destination_name=(
                    destination.name
                ),
                origin_index=origin_index,
                destination_index=(
                    destination_index
                ),
                duration_seconds=None,
                condition="ROUTE_NOT_FOUND",
            )
            for origin_index, origin
            in enumerate(locations)
            for destination_index, destination
            in enumerate(locations)
            if origin_index != destination_index
        ]

        return TravelTimeMatrixResult(
            matrix={},
            missing_elements=missing_elements,
        )


# TRANSIT Matrix가 완전히 비어도 다른 이동 방식 결과 유지
def test_plan_trip_preserves_other_modes_when_transit_matrix_is_empty():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    response = make_service(
        FakeRoutesProviderWithEmptyTransitMatrix()
    ).plan_trip(request)

    route_options_by_mode = {
        route_option.travel_mode: (
            route_option
        )
        for route_option
        in response
        .day_plans[0]
        .route_options
    }

    drive_option = route_options_by_mode[
        TravelMode.DRIVE
    ]
    walk_option = route_options_by_mode[
        TravelMode.WALK
    ]
    transit_option = route_options_by_mode[
        TravelMode.TRANSIT
    ]

    assert drive_option.timeline is not None
    assert walk_option.timeline is not None

    assert transit_option.timeline is None
    assert transit_option.ordered_stops == []
    assert transit_option.route_legs == []
    assert transit_option.total_travel_minutes == 0
    assert transit_option.missing_segments
    assert any(
        "완전한 경로를 생성할 수 없습니다"
        in warning
        for warning in transit_option.warnings
    )
