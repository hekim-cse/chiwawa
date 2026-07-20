# 정확 일자 배정 평가 지표와 결과 무결성을 검증하는 단위 테스트
from types import MappingProxyType

import pytest

from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)
from ai.route_planner.evaluation.day_assignment_evaluator import (
    DayAssignmentEvaluator,
)
from ai.route_planner.solvers.exact_day_assignment_solver import (
    ExactDayAssignmentResult,
)
from ai.route_planner.tests.test_day_assignment_solver import (
    make_request_payload,
)


# 정확 Solver 공개 인터페이스를 대신하는 테스트 대역
class StubExactDayAssignmentSolver:
    def __init__(self, result):
        self.result = result

    def solve(
        self,
        days,
        pois,
        travel_time_matrices_by_day,
    ):
        assert len(days) == 2
        assert len(pois) == 2
        assert set(
            travel_time_matrices_by_day
        ) == {1, 2}

        return self.result


# 모든 POI가 preferred 날짜에 배정된 결과 평가
def test_evaluates_complete_exact_assignment():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    exact_result = ExactDayAssignmentResult(
        assigned_poi_ids_by_day=(
            MappingProxyType(
                {
                    1: ("poi_a",),
                    2: ("poi_b",),
                }
            )
        ),
        unassigned_poi_ids=(),
        total_travel_minutes=30,
        evaluated_state_count=12,
    )

    result = DayAssignmentEvaluator(
        exact_day_assignment_solver=(
            StubExactDayAssignmentSolver(
                exact_result
            )
        )
    ).evaluate(
        scenario_id="evaluation-001",
        request=request,
        travel_time_matrices_by_day={
            1: {},
            2: {},
        },
    )

    assert result.scenario_id == (
        "evaluation-001"
    )
    assert result.total_travel_minutes == 30
    assert result.assigned_poi_count == 2
    assert result.unassigned_poi_count == 0
    assert (
        result.unassigned_must_visit_count
        == 0
    )
    assert (
        result.preferred_day_violation_count
        == 0
    )
    assert result.complete_assignment is True
    assert result.evaluated_state_count == 12
    assert result.runtime_ms >= 0

    assert [
        day.assigned_poi_ids
        for day in result.days
    ] == [
        ["poi_a"],
        ["poi_b"],
    ]


# 미배정 must_visit POI 수를 별도로 집계
def test_counts_unassigned_must_visit_pois():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    exact_result = ExactDayAssignmentResult(
        assigned_poi_ids_by_day=(
            MappingProxyType(
                {
                    1: (),
                    2: ("poi_b",),
                }
            )
        ),
        unassigned_poi_ids=("poi_a",),
        total_travel_minutes=20,
        evaluated_state_count=8,
    )

    result = DayAssignmentEvaluator(
        exact_day_assignment_solver=(
            StubExactDayAssignmentSolver(
                exact_result
            )
        )
    ).evaluate(
        scenario_id="partial",
        request=request,
        travel_time_matrices_by_day={
            1: {},
            2: {},
        },
    )

    assert result.assigned_poi_count == 1
    assert result.unassigned_poi_count == 1
    assert (
        result.unassigned_must_visit_count
        == 1
    )
    assert result.complete_assignment is False
    assert result.unassigned_poi_ids == [
        "poi_a"
    ]


# preferred 날짜를 위반한 비정상 결과를 평가 지표로 노출
def test_counts_preferred_day_violations():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    exact_result = ExactDayAssignmentResult(
        assigned_poi_ids_by_day=(
            MappingProxyType(
                {
                    1: ("poi_b",),
                    2: ("poi_a",),
                }
            )
        ),
        unassigned_poi_ids=(),
        total_travel_minutes=10,
        evaluated_state_count=3,
    )

    result = DayAssignmentEvaluator(
        exact_day_assignment_solver=(
            StubExactDayAssignmentSolver(
                exact_result
            )
        )
    ).evaluate(
        scenario_id="violation",
        request=request,
        travel_time_matrices_by_day={
            1: {},
            2: {},
        },
    )

    assert (
        result.preferred_day_violation_count
        == 2
    )


# 동일 POI가 여러 날짜에 포함된 비정상 결과 거부
def test_rejects_duplicate_assignment():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    exact_result = ExactDayAssignmentResult(
        assigned_poi_ids_by_day=(
            MappingProxyType(
                {
                    1: ("poi_a",),
                    2: ("poi_a", "poi_b"),
                }
            )
        ),
        unassigned_poi_ids=(),
        total_travel_minutes=10,
        evaluated_state_count=3,
    )

    with pytest.raises(
        ValueError,
        match="중복 배정",
    ):
        DayAssignmentEvaluator(
            exact_day_assignment_solver=(
                StubExactDayAssignmentSolver(
                    exact_result
                )
            )
        ).evaluate(
            scenario_id="duplicate",
            request=request,
            travel_time_matrices_by_day={
                1: {},
                2: {},
            },
        )
