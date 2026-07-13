# TimelineBuilder 단위 테스트
import pytest

from ai.route_planner.domain.schemas import TravelMode
from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    RouteOptionDTO,
)
from ai.route_planner.solvers.timeline_builder import TimelineBuilder
from ai.route_planner.tests.test_route_option_solver import (
    make_day_plan,
    make_travel_time_matrix,
)
from ai.route_planner.solvers.route_option_solver import RouteOptionSolver


# 테스트용 DayConstraintDTO 생성 함수
def make_day_constraint(
    start_time: str = "10:00",
    end_time: str = "20:00",
) -> DayConstraintDTO:
    return DayConstraintDTO(
        day_index=1,
        date="2026-08-01",
        start_place={
            "place_id": "start",
            "name": "출발지",
            "lat": 34.6657,
            "lng": 135.5010,
        },
        start_time=start_time,
        end_place={
            "place_id": "end",
            "name": "도착지",
            "lat": 34.7052,
            "lng": 135.4896,
        },
        end_time=end_time,
        max_place_count=4,
    )


# 테스트용 완전한 RouteOptionDTO 생성 함수
def make_route_option() -> RouteOptionDTO:
    day_plan = make_day_plan()

    return RouteOptionSolver().solve_route_option(
        day_plan=day_plan,
        travel_mode=TravelMode.DRIVE,
        travel_time_matrix=make_travel_time_matrix(),
    )


# 이동 시간과 POI 체류 시간을 순서대로 반영해 Timeline을 생성하는지 검증
def test_assign_timeline_builds_arrival_and_departure_times():
    day_plan = make_day_plan()
    route_option = make_route_option()
    builder = TimelineBuilder()

    updated_route_option = builder.assign_timeline(
        day_constraint=make_day_constraint(),
        day_plan=day_plan,
        route_option=route_option,
    )

    timeline = updated_route_option.timeline

    assert timeline is not None
    assert timeline.planned_start_at == "2026-08-01T10:00"
    assert timeline.actual_end_at == "2026-08-01T13:10"
    assert timeline.total_travel_minutes == 40
    assert timeline.total_stay_minutes == 150
    assert timeline.exceeds_planned_end is False

    assert timeline.timeline_stops[0].arrival_at == "2026-08-01T10:00"
    assert timeline.timeline_stops[0].departure_at == "2026-08-01T10:00"

    assert timeline.timeline_stops[1].arrival_at == "2026-08-01T10:10"
    assert timeline.timeline_stops[1].departure_at == "2026-08-01T11:10"

    assert timeline.timeline_stops[-1].arrival_at == "2026-08-01T13:10"
    assert timeline.timeline_stops[-1].departure_at == "2026-08-01T13:10"


# 원본 RouteOptionDTO는 수정하지 않고 새로운 DTO를 반환하는지 검증
def test_assign_timeline_does_not_mutate_original_route_option():
    day_plan = make_day_plan()
    route_option = make_route_option()
    builder = TimelineBuilder()

    updated_route_option = builder.assign_timeline(
        day_constraint=make_day_constraint(),
        day_plan=day_plan,
        route_option=route_option,
    )

    assert route_option.timeline is None
    assert updated_route_option.timeline is not None
    assert updated_route_option is not route_option


# 실제 종료 시간이 계획 종료 시간을 넘으면 warning이 생성되는지 검증
def test_assign_timeline_warns_when_schedule_exceeds_end_time():
    day_plan = make_day_plan()
    route_option = make_route_option()
    builder = TimelineBuilder()

    updated_route_option = builder.assign_timeline(
        day_constraint=make_day_constraint(
            end_time="12:00",
        ),
        day_plan=day_plan,
        route_option=route_option,
    )

    timeline = updated_route_option.timeline

    assert timeline is not None
    assert timeline.exceeds_planned_end is True
    assert any(
        "70분 초과" in warning
        for warning in timeline.warnings
    )


# 이동 구간이 누락된 RouteOptionDTO로는 Timeline을 생성하지 않는지 검증
def test_assign_timeline_rejects_route_option_with_missing_segments():
    day_plan = make_day_plan()
    route_option = make_route_option().model_copy(
        update={
            "missing_segments": [
                "a -> b",
            ]
        }
    )
    builder = TimelineBuilder()

    with pytest.raises(
        ValueError,
        match="missing segments",
    ):
        builder.assign_timeline(
            day_constraint=make_day_constraint(),
            day_plan=day_plan,
            route_option=route_option,
        )


# route_legs 순서가 ordered_stops와 다르면 예외가 발생하는지 검증
def test_assign_timeline_rejects_invalid_route_leg_order():
    day_plan = make_day_plan()
    route_option = make_route_option()

    invalid_first_leg = route_option.route_legs[0].model_copy(
        update={
            "destination_place_id": "invalid-place",
        }
    )
    invalid_route_option = route_option.model_copy(
        update={
            "route_legs": [
                invalid_first_leg,
                *route_option.route_legs[1:],
            ]
        }
    )
    builder = TimelineBuilder()

    with pytest.raises(
        ValueError,
        match="Route leg order",
    ):
        builder.assign_timeline(
            day_constraint=make_day_constraint(),
            day_plan=day_plan,
            route_option=invalid_route_option,
        )
