# ExactDayAssignmentSolver의 제약 조건과 사전식 전역 최적해 계산을 검증하는 단위 테스트
import pytest

from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    PoiDTO,
)
from ai.route_planner.solvers.exact_day_assignment_solver import (
    ExactDayAssignmentLimitExceededError,
    ExactDayAssignmentNotFoundError,
    ExactDayAssignmentSolver,
    ExactDayAssignmentSolverConfig,
    ExactDayAssignmentValidationError,
)


# 테스트용 날짜 DTO 생성
def make_day(
    day_index: int,
    max_place_count: int | None = None,
) -> DayConstraintDTO:
    return DayConstraintDTO.model_validate(
        {
            "day_index": day_index,
            "date": f"2026-08-{day_index:02d}",
            "start_place": {
                "place_id": f"day{day_index}_start",
                "name": f"{day_index}일차 출발지",
                "lat": 35.0 + day_index,
                "lng": 135.0 + day_index,
            },
            "start_time": "09:00",
            "end_place": {
                "place_id": f"day{day_index}_end",
                "name": f"{day_index}일차 도착지",
                "lat": 35.0 + day_index,
                "lng": 135.0 + day_index,
            },
            "end_time": "20:00",
            "max_place_count": max_place_count,
        }
    )


# 테스트용 POI DTO 생성
def make_poi(
    poi_id: str,
    *,
    priority: int = 3,
    must_visit: bool = False,
    preferred_day_index: int | None = None,
) -> PoiDTO:
    return PoiDTO.model_validate(
        {
            "poi_id": poi_id,
            "place_id": f"{poi_id}_place",
            "name": poi_id,
            "lat": 35.0,
            "lng": 135.0,
            "category": "TOURIST_ATTRACTION",
            "estimated_stay_minutes": 60,
            "priority": priority,
            "must_visit": must_visit,
            "preferred_day_index": (
                preferred_day_index
            ),
        }
    )


# 한 날짜의 START, POI, END 간 완전한 테스트 Matrix 생성
def make_complete_matrix(
    day: DayConstraintDTO,
    pois: list[PoiDTO],
    *,
    default_minutes: int = 50,
    overrides: dict[
        tuple[str, str],
        int,
    ]
    | None = None,
) -> dict[tuple[str, str], int]:
    place_ids = [
        day.start_place.place_id,
        *[
            poi.place_id
            for poi in pois
        ],
        day.end_place.place_id,
    ]

    matrix = {
        (origin, destination): (
            default_minutes
        )
        for origin in place_ids
        for destination in place_ids
        if origin != destination
    }

    matrix.update(overrides or {})

    return matrix


# 특정 날짜에 POI 하나를 방문하는 비용을 설정
def set_single_poi_route_cost(
    matrix: dict[tuple[str, str], int],
    day: DayConstraintDTO,
    poi: PoiDTO,
    total_minutes: int,
) -> None:
    start_minutes = total_minutes // 2
    end_minutes = (
        total_minutes - start_minutes
    )

    matrix[
        (
            day.start_place.place_id,
            poi.place_id,
        )
    ] = start_minutes
    matrix[
        (
            poi.place_id,
            day.end_place.place_id,
        )
    ] = end_minutes


# 날짜별 이동시간이 가장 작은 전역 배정을 선택
def test_assigns_pois_to_minimum_total_travel_days():
    day1 = make_day(1, max_place_count=1)
    day2 = make_day(2, max_place_count=1)

    poi_a = make_poi("poi_a")
    poi_b = make_poi("poi_b")
    pois = [poi_a, poi_b]

    day1_matrix = make_complete_matrix(
        day1,
        pois,
    )
    day2_matrix = make_complete_matrix(
        day2,
        pois,
    )

    set_single_poi_route_cost(
        day1_matrix,
        day1,
        poi_a,
        10,
    )
    set_single_poi_route_cost(
        day1_matrix,
        day1,
        poi_b,
        100,
    )
    set_single_poi_route_cost(
        day2_matrix,
        day2,
        poi_a,
        100,
    )
    set_single_poi_route_cost(
        day2_matrix,
        day2,
        poi_b,
        10,
    )

    result = ExactDayAssignmentSolver().solve(
        days=[day1, day2],
        pois=pois,
        travel_time_matrices_by_day={
            1: day1_matrix,
            2: day2_matrix,
        },
    )

    assert dict(
        result.assigned_poi_ids_by_day
    ) == {
        1: ("poi_a",),
        2: ("poi_b",),
    }
    assert result.unassigned_poi_ids == ()
    assert result.total_travel_minutes == 20
    assert result.evaluated_state_count > 0


# preferred_day_index를 다른 날짜 배정 후보에서 제외
def test_respects_preferred_day_as_hard_constraint():
    day1 = make_day(1, max_place_count=1)
    day2 = make_day(2, max_place_count=1)

    poi = make_poi(
        "preferred_poi",
        preferred_day_index=2,
    )

    day1_matrix = make_complete_matrix(
        day1,
        [poi],
    )
    day2_matrix = make_complete_matrix(
        day2,
        [poi],
    )

    set_single_poi_route_cost(
        day1_matrix,
        day1,
        poi,
        1,
    )
    set_single_poi_route_cost(
        day2_matrix,
        day2,
        poi,
        100,
    )

    result = ExactDayAssignmentSolver().solve(
        days=[day1, day2],
        pois=[poi],
        travel_time_matrices_by_day={
            1: day1_matrix,
            2: day2_matrix,
        },
    )

    assert dict(
        result.assigned_poi_ids_by_day
    ) == {
        1: (),
        2: ("preferred_poi",),
    }
    # 1일차 빈 경로 50분 + 2일차 preferred POI 경로 100분
    assert result.total_travel_minutes == 150


# max_place_count를 초과하는 부분집합을 생성하지 않음
def test_respects_max_place_count():
    day = make_day(
        1,
        max_place_count=1,
    )
    pois = [
        make_poi("poi_a"),
        make_poi("poi_b"),
    ]

    result = ExactDayAssignmentSolver().solve(
        days=[day],
        pois=pois,
        travel_time_matrices_by_day={
            1: make_complete_matrix(
                day,
                pois,
                default_minutes=1,
            )
        },
    )

    assert len(
        result.assigned_poi_ids_by_day[1]
    ) == 1
    assert len(
        result.unassigned_poi_ids
    ) == 1


# 수용량 부족 시 must_visit POI를 먼저 보존
def test_prioritizes_must_visit_when_capacity_is_insufficient():
    day = make_day(
        1,
        max_place_count=1,
    )
    must_visit_poi = make_poi(
        "must_visit_poi",
        must_visit=True,
        priority=5,
    )
    optional_poi = make_poi(
        "optional_poi",
        must_visit=False,
        priority=1,
    )
    pois = [
        must_visit_poi,
        optional_poi,
    ]

    matrix = make_complete_matrix(
        day,
        pois,
    )

    set_single_poi_route_cost(
        matrix,
        day,
        must_visit_poi,
        100,
    )
    set_single_poi_route_cost(
        matrix,
        day,
        optional_poi,
        1,
    )

    result = ExactDayAssignmentSolver().solve(
        days=[day],
        pois=pois,
        travel_time_matrices_by_day={
            1: matrix,
        },
    )

    assert (
        result.assigned_poi_ids_by_day[1]
        == ("must_visit_poi",)
    )
    assert result.unassigned_poi_ids == (
        "optional_poi",
    )


# must_visit 조건이 같으면 전체 배정 POI 수를 최대화
def test_maximizes_assigned_poi_count_before_travel_cost():
    day = make_day(
        1,
        max_place_count=2,
    )
    pois = [
        make_poi(
            "poi_a",
            must_visit=False,
        ),
        make_poi(
            "poi_b",
            must_visit=False,
        ),
    ]

    matrix = make_complete_matrix(
        day,
        pois,
        default_minutes=100,
    )

    result = ExactDayAssignmentSolver().solve(
        days=[day],
        pois=pois,
        travel_time_matrices_by_day={
            1: matrix,
        },
    )

    assert result.assigned_poi_ids_by_day[
        1
    ] == (
        "poi_a",
        "poi_b",
    )
    assert result.unassigned_poi_ids == ()


# 동일 배정 수에서는 priority 숫자가 작은 POI를 보존
def test_prioritizes_lower_priority_number():
    day = make_day(
        1,
        max_place_count=1,
    )
    high_priority_poi = make_poi(
        "high_priority",
        priority=1,
    )
    low_priority_poi = make_poi(
        "low_priority",
        priority=5,
    )
    pois = [
        high_priority_poi,
        low_priority_poi,
    ]

    matrix = make_complete_matrix(
        day,
        pois,
    )

    set_single_poi_route_cost(
        matrix,
        day,
        high_priority_poi,
        100,
    )
    set_single_poi_route_cost(
        matrix,
        day,
        low_priority_poi,
        1,
    )

    result = ExactDayAssignmentSolver().solve(
        days=[day],
        pois=pois,
        travel_time_matrices_by_day={
            1: matrix,
        },
    )

    assert (
        result.assigned_poi_ids_by_day[1]
        == ("high_priority",)
    )
    assert result.unassigned_poi_ids == (
        "low_priority",
    )


# Matrix 누락으로 완전 경로가 없는 부분집합 후보 제거
def test_excludes_subset_without_complete_route():
    day = make_day(
        1,
        max_place_count=2,
    )
    poi_a = make_poi("poi_a")
    poi_b = make_poi("poi_b")
    pois = [poi_a, poi_b]

    matrix = {
        (
            day.start_place.place_id,
            poi_a.place_id,
        ): 5,
        (
            poi_a.place_id,
            day.end_place.place_id,
        ): 5,
    }

    result = ExactDayAssignmentSolver().solve(
        days=[day],
        pois=pois,
        travel_time_matrices_by_day={
            1: matrix,
        },
    )

    assert result.assigned_poi_ids_by_day[
        1
    ] == ("poi_a",)
    assert result.unassigned_poi_ids == (
        "poi_b",
    )
    assert result.total_travel_minutes == 10


# POI가 없어도 날짜별 START에서 END까지의 직접 경로 비용을 계산
def test_returns_empty_assignment_without_pois():
    day1 = make_day(1)
    day2 = make_day(2)

    result = ExactDayAssignmentSolver().solve(
        days=[day1, day2],
        pois=[],
        travel_time_matrices_by_day={
            1: {
                (
                    day1.start_place.place_id,
                    day1.end_place.place_id,
                ): 7,
            },
            2: {
                (
                    day2.start_place.place_id,
                    day2.end_place.place_id,
                ): 11,
            },
        },
    )

    assert dict(
        result.assigned_poi_ids_by_day
    ) == {
        1: (),
        2: (),
    }
    assert result.unassigned_poi_ids == ()
    assert result.total_travel_minutes == 18


# 정확 계산 POI 제한 초과 시 fallback 없이 예외 발생
def test_rejects_poi_count_over_exact_limit():
    day = make_day(1)
    pois = [
        make_poi("poi_a"),
        make_poi("poi_b"),
    ]

    solver = ExactDayAssignmentSolver(
        config=(
            ExactDayAssignmentSolverConfig(
                max_poi_count=1
            )
        )
    )

    with pytest.raises(
        ExactDayAssignmentLimitExceededError,
        match="휴리스틱 fallback",
    ):
        solver.solve(
            days=[day],
            pois=pois,
            travel_time_matrices_by_day={
                1: make_complete_matrix(
                    day,
                    pois,
                )
            },
        )


# 날짜별 Matrix가 누락된 입력 거부
def test_rejects_missing_day_matrix():
    day1 = make_day(1)
    day2 = make_day(2)

    with pytest.raises(
        ExactDayAssignmentValidationError,
        match="Matrix가 누락",
    ):
        ExactDayAssignmentSolver().solve(
            days=[day1, day2],
            pois=[],
            travel_time_matrices_by_day={
                1: {},
            },
        )


# 요청에 존재하지 않는 preferred_day_index 거부
def test_rejects_unknown_preferred_day():
    day = make_day(1)
    poi = make_poi(
        "poi",
        preferred_day_index=2,
    )

    with pytest.raises(
        ExactDayAssignmentValidationError,
        match="해당하는 날짜가 없습니다",
    ):
        ExactDayAssignmentSolver().solve(
            days=[day],
            pois=[poi],
            travel_time_matrices_by_day={
                1: make_complete_matrix(
                    day,
                    [poi],
                )
            },
        )


# POI가 없는 날짜도 START에서 END까지의 실제 이동시간을 합산
def test_counts_direct_route_cost_for_empty_day():
    day1 = make_day(1, max_place_count=1)
    day2 = make_day(2, max_place_count=1)
    poi = make_poi("poi")

    day1_matrix = make_complete_matrix(
        day1,
        [poi],
        default_minutes=50,
    )
    day2_matrix = make_complete_matrix(
        day2,
        [poi],
        default_minutes=50,
    )

    day1_matrix[
        (
            day1.start_place.place_id,
            day1.end_place.place_id,
        )
    ] = 7
    day2_matrix[
        (
            day2.start_place.place_id,
            day2.end_place.place_id,
        )
    ] = 11

    set_single_poi_route_cost(
        day1_matrix,
        day1,
        poi,
        10,
    )
    set_single_poi_route_cost(
        day2_matrix,
        day2,
        poi,
        100,
    )

    result = ExactDayAssignmentSolver().solve(
        days=[day1, day2],
        pois=[poi],
        travel_time_matrices_by_day={
            1: day1_matrix,
            2: day2_matrix,
        },
    )

    assert dict(
        result.assigned_poi_ids_by_day
    ) == {
        1: ("poi",),
        2: (),
    }
    assert result.total_travel_minutes == 21


# 빈 일자의 START에서 END까지 직접 경로도 없으면 유효한 전체 배정 부재
def test_rejects_assignment_when_day_has_no_valid_route():
    day = make_day(1)

    with pytest.raises(
        ExactDayAssignmentNotFoundError,
        match="유효한 정확 일자 배정",
    ):
        ExactDayAssignmentSolver().solve(
            days=[day],
            pois=[],
            travel_time_matrices_by_day={
                1: {},
            },
        )
