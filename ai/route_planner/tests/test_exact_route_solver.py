# ExactRouteSolver 단위 테스트
from itertools import permutations

import pytest

from ai.route_planner.solvers.exact_route_solver import (
    ExactRouteLimitExceededError,
    ExactRouteNotFoundError,
    ExactRouteSolver,
    ExactRouteSolverConfig,
)


# 비대칭 이동시간 Matrix
def make_matrix():
    return {
        ("start", "a"): 10,
        ("start", "b"): 30,
        ("start", "c"): 50,
        ("start", "end"): 100,
        ("a", "b"): 10,
        ("a", "c"): 30,
        ("a", "end"): 80,
        ("b", "a"): 10,
        ("b", "c"): 10,
        ("b", "end"): 40,
        ("c", "a"): 30,
        ("c", "b"): 10,
        ("c", "end"): 10,
    }


# 작은 입력의 모든 순열을 검사해 전역 최솟값 계산
def calculate_bruteforce_minimum(
    poi_ids,
    matrix,
):
    candidates = []

    for ordered_pois in permutations(poi_ids):
        route = (
            "start",
            *ordered_pois,
            "end",
        )
        total = 0

        for origin, destination in zip(
            route,
            route[1:],
        ):
            travel_minutes = matrix.get(
                (origin, destination)
            )

            if travel_minutes is None:
                break

            total += travel_minutes
        else:
            candidates.append(
                (total, route)
            )

    return min(candidates)


# 모든 순열의 최솟값과 정확히 같은 결과를 반환
def test_solve_returns_global_optimum():
    matrix = make_matrix()
    expected_total, expected_route = (
        calculate_bruteforce_minimum(
            poi_ids=["a", "b", "c"],
            matrix=matrix,
        )
    )

    result = ExactRouteSolver().solve(
        start_place_id="start",
        poi_place_ids=["a", "b", "c"],
        end_place_id="end",
        travel_time_matrix=matrix,
    )

    assert result.total_travel_minutes == expected_total
    assert result.ordered_place_ids == expected_route
    assert result.ordered_place_ids == (
        "start",
        "a",
        "b",
        "c",
        "end",
    )
    assert result.total_travel_minutes == 40
    assert result.evaluated_state_count > 0


# POI가 없으면 출발지에서 도착지까지 직접 연결
def test_solve_handles_empty_pois():
    result = ExactRouteSolver().solve(
        start_place_id="start",
        poi_place_ids=[],
        end_place_id="end",
        travel_time_matrix={
            ("start", "end"): 25,
        },
    )

    assert result.ordered_place_ids == (
        "start",
        "end",
    )
    assert result.total_travel_minutes == 25
    assert result.evaluated_state_count == 1


# 일부 간선이 없어도 완전 경로가 존재하면 정확히 탐색
def test_solve_uses_available_complete_route():
    result = ExactRouteSolver().solve(
        start_place_id="start",
        poi_place_ids=["a", "b"],
        end_place_id="end",
        travel_time_matrix={
            ("start", "a"): 5,
            ("a", "b"): 7,
            ("b", "end"): 11,
        },
    )

    assert result.ordered_place_ids == (
        "start",
        "a",
        "b",
        "end",
    )
    assert result.total_travel_minutes == 23


# 모든 POI를 포함하는 완전 경로가 없으면 명시적으로 실패
def test_solve_rejects_incomplete_route():
    with pytest.raises(
        ExactRouteNotFoundError,
        match="완전 경로가 없습니다",
    ):
        ExactRouteSolver().solve(
            start_place_id="start",
            poi_place_ids=["a", "b", "c"],
            end_place_id="end",
            travel_time_matrix={
                ("start", "a"): 10,
                ("a", "end"): 10,
            },
        )


# POI가 없는 경우에도 직접 구간이 없으면 명시적으로 실패
def test_solve_rejects_missing_direct_route():
    with pytest.raises(
        ExactRouteNotFoundError,
        match="이동 구간이 없습니다",
    ):
        ExactRouteSolver().solve(
            start_place_id="start",
            poi_place_ids=[],
            end_place_id="end",
            travel_time_matrix={},
        )


# 설정된 정확 계산 제한을 넘으면 fallback 없이 실패
def test_solve_rejects_limit_exceeded():
    solver = ExactRouteSolver(
        config=ExactRouteSolverConfig(
            max_poi_count=2,
        )
    )

    with pytest.raises(
        ExactRouteLimitExceededError,
        match="휴리스틱 fallback은 사용하지 않습니다",
    ):
        solver.solve(
            start_place_id="start",
            poi_place_ids=["a", "b", "c"],
            end_place_id="end",
            travel_time_matrix=make_matrix(),
        )


# place_id 중복 입력을 거부
def test_solve_rejects_duplicate_place_ids():
    with pytest.raises(
        ValueError,
        match="중복될 수 없습니다",
    ):
        ExactRouteSolver().solve(
            start_place_id="start",
            poi_place_ids=["a", "a"],
            end_place_id="end",
            travel_time_matrix={},
        )
