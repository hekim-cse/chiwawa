# 정확 경로 최적화 Evaluator 단위 테스트
import pytest

from ai.route_planner.domain.schemas import (
    TravelMode,
)
from ai.route_planner.evaluation.route_evaluator import (
    RouteEvaluator,
)
from ai.route_planner.evaluation.schemas import (
    RouteEvaluationStage,
)
from ai.route_planner.solvers.exact_route_solver import (
    ExactRouteLimitExceededError,
    ExactRouteSolver,
    ExactRouteSolverConfig,
)
from ai.route_planner.tests.test_route_option_solver import (
    make_day_plan,
)


# 입력 순서보다 정확 최적 경로가 짧아지는 Matrix
def make_evaluation_matrix():
    return {
        ("start", "a"): 50,
        ("start", "b"): 10,
        ("start", "c"): 30,
        ("start", "end"): 100,
        ("a", "b"): 30,
        ("a", "c"): 10,
        ("a", "end"): 10,
        ("b", "a"): 10,
        ("b", "c"): 50,
        ("b", "end"): 30,
        ("c", "a"): 50,
        ("c", "b"): 10,
        ("c", "end"): 10,
    }


# Baseline과 정확 동적 계획법 평가 결과 생성
def test_evaluate_returns_exact_route_result():
    result = RouteEvaluator().evaluate(
        scenario_id="route-evaluation-001",
        day_plan=make_day_plan(),
        travel_mode=TravelMode.DRIVE,
        travel_time_matrix=(
            make_evaluation_matrix()
        ),
    )

    assert result.scenario_id == (
        "route-evaluation-001"
    )
    assert result.travel_mode == TravelMode.DRIVE

    assert (
        result.baseline.stage
        == RouteEvaluationStage.BASELINE
    )
    assert (
        result.exact_dynamic_programming.stage
        == RouteEvaluationStage
        .EXACT_DYNAMIC_PROGRAMMING
    )

    assert (
        result.baseline.total_travel_minutes
        == 140
    )
    assert (
        result.exact_dynamic_programming
        .total_travel_minutes
        == 40
    )
    assert (
        result.exact_dynamic_programming
        .ordered_place_ids
        == [
            "start",
            "b",
            "a",
            "c",
            "end",
        ]
    )

    assert result.improvement_minutes == 100
    assert result.improvement_ratio == 71.4286
    assert result.evaluated_state_count > 0
    assert result.complete_route_found is True


# 정확 경로가 모든 POI를 정확히 한 번 포함
def test_evaluate_preserves_route_invariants():
    result = RouteEvaluator().evaluate(
        scenario_id="route-invariants",
        day_plan=make_day_plan(),
        travel_mode=TravelMode.WALK,
        travel_time_matrix=(
            make_evaluation_matrix()
        ),
    )

    ordered_place_ids = (
        result.exact_dynamic_programming
        .ordered_place_ids
    )

    assert ordered_place_ids[0] == "start"
    assert ordered_place_ids[-1] == "end"

    poi_place_ids = ordered_place_ids[1:-1]

    assert len(poi_place_ids) == len(
        set(poi_place_ids)
    )
    assert set(poi_place_ids) == {
        "a",
        "b",
        "c",
    }


# Baseline이 불완전해도 다른 완전 경로가 존재하면 정확 계산
def test_evaluate_finds_complete_route_when_baseline_is_missing():
    result = RouteEvaluator().evaluate(
        scenario_id="baseline-missing",
        day_plan=make_day_plan(),
        travel_mode=TravelMode.TRANSIT,
        travel_time_matrix={
            ("start", "b"): 10,
            ("b", "a"): 10,
            ("a", "c"): 10,
            ("c", "end"): 10,
        },
    )

    assert (
        result.baseline.total_travel_minutes
        is None
    )
    assert result.baseline.missing_segments

    assert (
        result.exact_dynamic_programming
        .total_travel_minutes
        == 40
    )
    assert (
        result.exact_dynamic_programming
        .ordered_place_ids
        == [
            "start",
            "b",
            "a",
            "c",
            "end",
        ]
    )
    assert result.complete_route_found is True
    assert result.improvement_minutes is None
    assert result.improvement_ratio is None


# 모든 POI를 방문하는 경로가 없으면 부분 경로 없이 기록
def test_evaluate_records_complete_route_not_found():
    result = RouteEvaluator().evaluate(
        scenario_id="route-not-found",
        day_plan=make_day_plan(),
        travel_mode=TravelMode.TRANSIT,
        travel_time_matrix={
            ("start", "a"): 10,
            ("a", "end"): 10,
        },
    )

    assert result.complete_route_found is False
    assert result.evaluated_state_count == 0

    exact_stage = (
        result.exact_dynamic_programming
    )

    assert exact_stage.ordered_place_ids == []
    assert exact_stage.total_travel_minutes is None
    assert exact_stage.missing_segments
    assert result.improvement_minutes is None
    assert result.improvement_ratio is None


# 정확 계산 제한 초과 시 휴리스틱으로 전환하지 않고 예외 전파
def test_evaluate_propagates_exact_route_limit():
    evaluator = RouteEvaluator(
        exact_route_solver=ExactRouteSolver(
            config=ExactRouteSolverConfig(
                max_poi_count=2,
            )
        )
    )

    with pytest.raises(
        ExactRouteLimitExceededError,
        match="휴리스틱 fallback은 사용하지 않습니다",
    ):
        evaluator.evaluate(
            scenario_id="route-limit",
            day_plan=make_day_plan(),
            travel_mode=TravelMode.DRIVE,
            travel_time_matrix=(
                make_evaluation_matrix()
            ),
        )
