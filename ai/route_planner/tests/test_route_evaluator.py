# RouteEvaluator 단계별 경로 평가 테스트
from ai.route_planner.domain.schemas import (
    TravelMode,
)
from ai.route_planner.domain.trip_schemas import (
    PoiCategory,
    PoiDTO,
)
from ai.route_planner.evaluation.route_evaluator import (
    RouteEvaluator,
)
from ai.route_planner.evaluation.schemas import (
    RouteEvaluationStage,
)
from ai.route_planner.tests.test_route_option_solver import (
    make_day_plan,
)


# 입력 순서보다 Cheapest Insertion 결과가 짧아지는 Matrix
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


# Relocate와 2-opt 평가를 위해 POI d를 추가한 DayPlan 생성
def make_four_poi_day_plan():
    base_day_plan = make_day_plan()

    poi_d = PoiDTO(
        poi_id="poi_004",
        place_id="d",
        name="D 장소",
        lat=34.7000,
        lng=135.4900,
        category=PoiCategory.ACTIVITY,
        estimated_stay_minutes=45,
        priority=2,
        must_visit=True,
        preferred_day_index=1,
    )

    assigned_pois = [
        *base_day_plan.assigned_pois,
        poi_d,
    ]

    return base_day_plan.model_copy(
        update={
            "assigned_pois": assigned_pois,
            "estimated_total_stay_minutes": sum(
                poi.estimated_stay_minutes
                for poi in assigned_pois
            ),
        }
    )


# 모든 평가 단계와 비용 개선 결과가 생성되는지 검증
def test_evaluate_returns_route_stage_results():
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
        result.cheapest_insertion.stage
        == RouteEvaluationStage.CHEAPEST_INSERTION
    )
    assert (
        result.relocate.stage
        == RouteEvaluationStage.RELOCATE
    )
    assert (
        result.two_opt.stage
        == RouteEvaluationStage.TWO_OPT
    )
    assert (
        result.final_local_search.stage
        == RouteEvaluationStage.FINAL_LOCAL_SEARCH
    )

    assert (
        result.baseline.total_travel_minutes
        == 140
    )
    assert (
        result.cheapest_insertion
        .total_travel_minutes
        == 40
    )

    assert (
        result.cheapest_insertion
        .improvement_minutes_from_baseline
        == 100
    )
    assert (
        result.cheapest_insertion
        .improvement_ratio_from_baseline
        == 71.4286
    )

    assert (
        result.final_local_search
        .total_travel_minutes
        <= result.cheapest_insertion
        .total_travel_minutes
    )

    assert result.uninserted_place_ids == []


# 모든 단계에서 START, END와 POI 집합이 유지되는지 검증
def test_evaluate_preserves_route_invariants():
    result = RouteEvaluator().evaluate(
        scenario_id="route-invariants",
        day_plan=make_day_plan(),
        travel_mode=TravelMode.WALK,
        travel_time_matrix=(
            make_evaluation_matrix()
        ),
    )

    stages = [
        result.baseline,
        result.cheapest_insertion,
        result.relocate,
        result.two_opt,
        result.final_local_search,
    ]

    for stage in stages:
        assert stage.ordered_place_ids[0] == "start"
        assert stage.ordered_place_ids[-1] == "end"

        poi_place_ids = (
            stage.ordered_place_ids[1:-1]
        )

        assert len(poi_place_ids) == len(
            set(poi_place_ids)
        )
        assert set(poi_place_ids) == {
            "a",
            "b",
            "c",
        }


# Matrix 누락 시 가짜 비용을 사용하지 않고 None과 누락 구간을 유지하는지 검증
def test_evaluate_preserves_missing_matrix_segments():
    result = RouteEvaluator().evaluate(
        scenario_id="route-missing-matrix",
        day_plan=make_day_plan(),
        travel_mode=TravelMode.TRANSIT,
        travel_time_matrix={
            ("start", "a"): 10,
            ("a", "end"): 10,
        },
    )

    assert (
        result.baseline.total_travel_minutes
        is None
    )
    assert result.baseline.missing_segments

    assert (
        result.cheapest_insertion
        .total_travel_minutes
        == 20
    )
    assert result.uninserted_place_ids == [
        "b",
        "c",
    ]

    assert (
        result.cheapest_insertion
        .improvement_ratio_from_baseline
        is None
    )
    assert (
        result.final_local_search
        .total_travel_minutes
        == 20
    )


# Cheapest Insertion 이후 Relocate가 추가로 경로를 줄이는 Matrix
def make_relocate_improvement_matrix():
    return {
        ("start", "a"): 24,
        ("start", "b"): 3,
        ("start", "c"): 37,
        ("start", "d"): 44,
        ("start", "end"): 3,
        ("a", "b"): 17,
        ("a", "c"): 18,
        ("a", "d"): 5,
        ("a", "end"): 35,
        ("b", "a"): 37,
        ("b", "c"): 8,
        ("b", "d"): 12,
        ("b", "end"): 31,
        ("c", "a"): 25,
        ("c", "b"): 17,
        ("c", "d"): 29,
        ("c", "end"): 4,
        ("d", "a"): 22,
        ("d", "b"): 3,
        ("d", "c"): 9,
        ("d", "end"): 16,
    }


# Relocate 단계가 Cheapest Insertion 결과를 실제로 개선하는지 검증
def test_evaluate_measures_relocate_improvement():
    result = RouteEvaluator().evaluate(
        scenario_id="route-relocate-improvement",
        day_plan=make_four_poi_day_plan(),
        travel_mode=TravelMode.DRIVE,
        travel_time_matrix=(
            make_relocate_improvement_matrix()
        ),
    )

    assert (
        result.cheapest_insertion
        .ordered_place_ids
        == [
            "start",
            "b",
            "a",
            "d",
            "c",
            "end",
        ]
    )
    assert (
        result.cheapest_insertion
        .total_travel_minutes
        == 58
    )

    assert result.relocate.ordered_place_ids == [
        "start",
        "a",
        "d",
        "b",
        "c",
        "end",
    ]
    assert (
        result.relocate.total_travel_minutes
        == 44
    )
    assert (
        result.relocate
        .improvement_minutes_from_previous
        == 14
    )
    assert (
        result.relocate
        .improvement_ratio_from_previous
        == 24.1379
    )

    assert (
        result.two_opt.total_travel_minutes
        == 44
    )
    assert (
        result.final_local_search
        .total_travel_minutes
        == 44
    )


# Relocate는 개선하지 못하지만 2-opt가 추가로 경로를 줄이는 Matrix
def make_two_opt_improvement_matrix():
    return {
        ("start", "a"): 39,
        ("start", "b"): 1,
        ("start", "c"): 14,
        ("start", "d"): 20,
        ("start", "end"): 15,
        ("a", "b"): 30,
        ("a", "c"): 11,
        ("a", "d"): 50,
        ("a", "end"): 41,
        ("b", "a"): 14,
        ("b", "c"): 44,
        ("b", "d"): 41,
        ("b", "end"): 21,
        ("c", "a"): 3,
        ("c", "b"): 23,
        ("c", "d"): 42,
        ("c", "end"): 29,
        ("d", "a"): 46,
        ("d", "b"): 50,
        ("d", "c"): 27,
        ("d", "end"): 48,
    }


# 2-opt 단계가 Relocate 결과를 실제로 개선하는지 검증
def test_evaluate_measures_two_opt_improvement():
    result = RouteEvaluator().evaluate(
        scenario_id="route-two-opt-improvement",
        day_plan=make_four_poi_day_plan(),
        travel_mode=TravelMode.DRIVE,
        travel_time_matrix=(
            make_two_opt_improvement_matrix()
        ),
    )

    assert (
        result.cheapest_insertion
        .ordered_place_ids
        == [
            "start",
            "b",
            "a",
            "c",
            "d",
            "end",
        ]
    )
    assert (
        result.cheapest_insertion
        .total_travel_minutes
        == 116
    )

    assert (
        result.relocate.total_travel_minutes
        == 116
    )
    assert (
        result.relocate
        .improvement_minutes_from_previous
        == 0
    )

    assert result.two_opt.ordered_place_ids == [
        "start",
        "d",
        "c",
        "a",
        "b",
        "end",
    ]
    assert (
        result.two_opt.total_travel_minutes
        == 101
    )
    assert (
        result.two_opt
        .improvement_minutes_from_previous
        == 15
    )
    assert (
        result.two_opt
        .improvement_ratio_from_previous
        == 12.931
    )

    assert (
        result.final_local_search
        .total_travel_minutes
        == 101
    )
