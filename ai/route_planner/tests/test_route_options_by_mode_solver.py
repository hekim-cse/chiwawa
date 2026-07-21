# RouteOptionsByModeSolver 단위 테스트
import pytest

from ai.route_planner.domain.schemas import (
    TravelMode,
    TravelTimeElement,
    TravelTimeMatrixResult,
)
from ai.route_planner.solvers.route_options_by_mode_solver import (
    RouteOptionsByModeSolver,
)
from ai.route_planner.tests.test_route_option_solver import make_day_plan


# 테스트용 정상 이동 시간 행렬 결과를 생성하는 함수
def make_matrix_result(
    travel_minutes: int,
) -> TravelTimeMatrixResult:
    place_ids = [
        "start",
        "a",
        "b",
        "c",
        "end",
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


# DRIVE, WALK, TRANSIT Route Option이 설정 순서대로 생성되는지 검증
def test_assign_route_options_adds_all_travel_modes():
    day_plan = make_day_plan()
    solver = RouteOptionsByModeSolver()

    updated_day_plan = solver.assign_route_options(
        day_plan=day_plan,
        matrix_results_by_mode={
            TravelMode.DRIVE: make_matrix_result(10),
            TravelMode.WALK: make_matrix_result(20),
            TravelMode.TRANSIT: make_matrix_result(15),
        },
    )

    travel_modes = [
        route_option.travel_mode
        for route_option in updated_day_plan.route_options
    ]

    assert travel_modes == [
        TravelMode.DRIVE,
        TravelMode.WALK,
        TravelMode.TRANSIT,
    ]
    assert len(updated_day_plan.route_options) == 3


# 원본 DayPlanDTO는 변경하지 않고 새로운 DayPlanDTO를 반환하는지 검증
def test_assign_route_options_does_not_mutate_original_day_plan():
    day_plan = make_day_plan()
    solver = RouteOptionsByModeSolver()

    updated_day_plan = solver.assign_route_options(
        day_plan=day_plan,
        matrix_results_by_mode={
            TravelMode.DRIVE: make_matrix_result(10),
            TravelMode.WALK: make_matrix_result(20),
            TravelMode.TRANSIT: make_matrix_result(15),
        },
    )

    assert day_plan.route_options == []
    assert len(updated_day_plan.route_options) == 3
    assert updated_day_plan is not day_plan


# 설정된 이동 방식의 matrix 결과가 없으면 ValueError가 발생하는지 검증
def test_assign_route_options_raises_error_when_mode_is_missing():
    day_plan = make_day_plan()
    solver = RouteOptionsByModeSolver()

    with pytest.raises(
        ValueError,
        match="TRANSIT",
    ):
        solver.assign_route_options(
            day_plan=day_plan,
            matrix_results_by_mode={
                TravelMode.DRIVE: make_matrix_result(10),
                TravelMode.WALK: make_matrix_result(20),
            },
        )


# Provider 누락 구간이 RouteOptionDTO의 missing_segments와 warnings에 반영되는지 검증
def test_assign_route_options_tracks_provider_missing_segments():
    day_plan = make_day_plan()
    solver = RouteOptionsByModeSolver()

    transit_result = make_matrix_result(15)
    transit_result = transit_result.model_copy(
        update={
            "missing_elements": [
                TravelTimeElement(
                    origin_name="a",
                    destination_name="end",
                    origin_index=1,
                    destination_index=4,
                    duration_seconds=None,
                    condition="ROUTE_NOT_FOUND",
                )
            ]
        }
    )

    updated_day_plan = solver.assign_route_options(
        day_plan=day_plan,
        matrix_results_by_mode={
            TravelMode.DRIVE: make_matrix_result(10),
            TravelMode.WALK: make_matrix_result(20),
            TravelMode.TRANSIT: transit_result,
        },
    )

    transit_option = next(
        route_option
        for route_option in updated_day_plan.route_options
        if route_option.travel_mode == TravelMode.TRANSIT
    )

    assert "a -> end" in transit_option.missing_segments
    assert any(
        "Google Routes Provider" in warning
        for warning in transit_option.warnings
    )


# 실제 API 호출 없이 실행 스크립트의 전체 연결 흐름을 검증
def test_run_route_options_by_mode_returns_day_plans_with_three_options():
    from ai.route_planner.domain.schemas import TravelTimeMatrixResult
    from ai.route_planner.domain.trip_schemas import TripPlanningRequestDTO
    from ai.route_planner.scripts.run_route_options_by_mode import (
        run_route_options_by_mode,
    )
    from ai.route_planner.tests.test_route_option_solver import (
        make_request_payload,
    )

    class FakeGoogleRoutesProvider:
        def build_travel_time_matrix_result(
            self,
            locations,
            travel_mode,
            departure_time=None,
        ):
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

            return TravelTimeMatrixResult(
                matrix=matrix,
                missing_elements=[],
            )

    request = TripPlanningRequestDTO.model_validate(
        make_request_payload()
    )

    response_payload = run_route_options_by_mode(
        request=request,
        routes_provider=FakeGoogleRoutesProvider(),
    )

    route_options = response_payload["day_plans"][0]["route_options"]

    assert len(route_options) == 3
    assert [
        route_option["travel_mode"]
        for route_option in route_options
    ] == [
        "DRIVE",
        "WALK",
        "TRANSIT",
    ]


# Provider Matrix가 비어 있는 이동 방식만 사용 불가 옵션으로 격리
def test_assign_route_options_returns_unavailable_option_for_empty_matrix():
    day_plan = make_day_plan()

    place_ids = [
        day_plan.start_place.place_id,
        *[
            poi.place_id
            for poi in day_plan.assigned_pois
        ],
        day_plan.end_place.place_id,
    ]

    complete_result = (
        TravelTimeMatrixResult(
            matrix={
                (
                    origin,
                    destination,
                ): 10
                for origin in place_ids
                for destination in place_ids
                if origin != destination
            },
            missing_elements=[],
        )
    )

    transit_result = (
        TravelTimeMatrixResult(
            matrix={},
            missing_elements=[
                TravelTimeElement(
                    origin_name="start",
                    destination_name="poi",
                    origin_index=0,
                    destination_index=1,
                    duration_seconds=None,
                    condition="ROUTE_NOT_FOUND",
                ),
                TravelTimeElement(
                    origin_name="poi",
                    destination_name="end",
                    origin_index=1,
                    destination_index=2,
                    duration_seconds=None,
                    condition="ROUTE_NOT_FOUND",
                ),
            ],
        )
    )

    result = RouteOptionsByModeSolver().assign_route_options(
        day_plan=day_plan,
        matrix_results_by_mode={
            TravelMode.DRIVE: complete_result,
            TravelMode.WALK: complete_result,
            TravelMode.TRANSIT: transit_result,
        },
    )

    options_by_mode = {
        option.travel_mode: option
        for option in result.route_options
    }

    assert options_by_mode[
        TravelMode.DRIVE
    ].ordered_stops

    assert options_by_mode[
        TravelMode.WALK
    ].ordered_stops

    transit_option = options_by_mode[
        TravelMode.TRANSIT
    ]

    assert transit_option.ordered_stops == []
    assert transit_option.route_legs == []
    assert transit_option.missing_segments
    assert transit_option.warnings
