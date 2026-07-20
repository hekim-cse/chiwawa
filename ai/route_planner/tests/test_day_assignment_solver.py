# 정확 일자 배정 결과의 DayPlanDTO 변환과 응답 상태를 검증하는 단위 테스트
from dataclasses import dataclass
from types import MappingProxyType

import pytest

from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
    TripPlanningStatus,
)
from ai.route_planner.solvers.day_assignment_solver import (
    DayAssignmentSolver,
    DayAssignmentSolverConfig,
)
from ai.route_planner.solvers.exact_day_assignment_solver import (
    ExactDayAssignmentResult,
)


# 테스트용 여행 요청 payload 생성
def make_request_payload() -> dict:
    return {
        "trip_id": "trip_001",
        "timezone": "Asia/Tokyo",
        "days": [
            {
                "day_index": 1,
                "date": "2026-08-01",
                "start_place": {
                    "place_id": "day1_start",
                    "name": "1일차 출발지",
                    "lat": 35.0,
                    "lng": 135.0,
                },
                "start_time": "09:00",
                "end_place": {
                    "place_id": "day1_end",
                    "name": "1일차 도착지",
                    "lat": 35.0,
                    "lng": 135.0,
                },
                "end_time": "20:00",
                "max_place_count": 2,
            },
            {
                "day_index": 2,
                "date": "2026-08-02",
                "start_place": {
                    "place_id": "day2_start",
                    "name": "2일차 출발지",
                    "lat": 36.0,
                    "lng": 136.0,
                },
                "start_time": "09:00",
                "end_place": {
                    "place_id": "day2_end",
                    "name": "2일차 도착지",
                    "lat": 36.0,
                    "lng": 136.0,
                },
                "end_time": "20:00",
                "max_place_count": 2,
            },
        ],
        "pois": [
            {
                "poi_id": "poi_a",
                "place_id": "place_a",
                "name": "장소 A",
                "lat": 35.1,
                "lng": 135.1,
                "category": "TOURIST_ATTRACTION",
                "estimated_stay_minutes": 60,
                "priority": 1,
                "must_visit": True,
                "preferred_day_index": 1,
            },
            {
                "poi_id": "poi_b",
                "place_id": "place_b",
                "name": "장소 B",
                "lat": 36.1,
                "lng": 136.1,
                "category": "CAFE",
                "estimated_stay_minutes": 90,
                "priority": 2,
                "must_visit": False,
                "preferred_day_index": 2,
            },
        ],
    }


# ExactDayAssignmentSolver 공개 인터페이스를 대신하는 테스트 대역
@dataclass
class StubExactDayAssignmentSolver:
    result: ExactDayAssignmentResult

    def solve(
        self,
        days,
        pois,
        travel_time_matrices_by_day,
    ) -> ExactDayAssignmentResult:
        assert len(days) == 2
        assert len(pois) == 2
        assert set(
            travel_time_matrices_by_day
        ) == {1, 2}

        return self.result


# 성공 정확 배정 결과 생성
def make_success_result() -> (
    ExactDayAssignmentResult
):
    return ExactDayAssignmentResult(
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
        evaluated_state_count=8,
    )


# 정확 배정 결과를 날짜별 DayPlanDTO로 변환
def test_builds_day_plans_from_exact_assignment():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )
    solver = DayAssignmentSolver(
        exact_day_assignment_solver=(
            StubExactDayAssignmentSolver(
                make_success_result()
            )
        )
    )

    response = solver.assign_pois_to_days(
        request=request,
        travel_time_matrices_by_day={
            1: {},
            2: {},
        },
    )

    assert (
        response.status
        == TripPlanningStatus.SUCCESS
    )
    assert response.unassigned_pois == []
    assert response.warnings == []
    assert len(response.day_plans) == 2

    assert [
        poi.poi_id
        for poi in (
            response
            .day_plans[0]
            .assigned_pois
        )
    ] == ["poi_a"]

    assert [
        poi.poi_id
        for poi in (
            response
            .day_plans[1]
            .assigned_pois
        )
    ] == ["poi_b"]

    assert (
        response
        .day_plans[0]
        .estimated_total_stay_minutes
        == 60
    )
    assert (
        response
        .day_plans[1]
        .estimated_total_stay_minutes
        == 90
    )
    assert all(
        day_plan.assignment_reason
        == "정확 일자 배정 최적화 결과"
        for day_plan in response.day_plans
    )


# 미배정 POI가 있으면 PARTIAL_SUCCESS와 사유 반환
def test_returns_partial_success_with_unassigned_poi():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    result = ExactDayAssignmentResult(
        assigned_poi_ids_by_day=(
            MappingProxyType(
                {
                    1: ("poi_a",),
                    2: (),
                }
            )
        ),
        unassigned_poi_ids=("poi_b",),
        total_travel_minutes=20,
        evaluated_state_count=5,
    )

    response = DayAssignmentSolver(
        exact_day_assignment_solver=(
            StubExactDayAssignmentSolver(
                result
            )
        )
    ).assign_pois_to_days(
        request=request,
        travel_time_matrices_by_day={
            1: {},
            2: {},
        },
    )

    assert (
        response.status
        == TripPlanningStatus.PARTIAL_SUCCESS
    )
    assert len(response.unassigned_pois) == 1
    assert (
        response
        .unassigned_pois[0]
        .poi.poi_id
        == "poi_b"
    )
    assert (
        "정확 배정되지 못함"
        in response
        .unassigned_pois[0]
        .reason
    )


# 체류시간이 날짜 이용 가능 시간을 초과하면 경고 반환
def test_warns_when_stay_time_exceeds_available_time():
    payload = make_request_payload()
    payload["days"][0]["end_time"] = "09:30"
    payload["pois"][0][
        "estimated_stay_minutes"
    ] = 60

    request = (
        TripPlanningRequestDTO
        .model_validate(payload)
    )

    response = DayAssignmentSolver(
        exact_day_assignment_solver=(
            StubExactDayAssignmentSolver(
                make_success_result()
            )
        )
    ).assign_pois_to_days(
        request=request,
        travel_time_matrices_by_day={
            1: {},
            2: {},
        },
    )

    assert len(response.warnings) == 1
    assert (
        "day_index=1"
        in response.warnings[0]
    )
    assert "stay=60" in response.warnings[0]
    assert "available=30" in response.warnings[0]


# 설정으로 체류시간 초과 경고 비활성화
def test_can_disable_stay_time_warning():
    payload = make_request_payload()
    payload["days"][0]["end_time"] = "09:30"

    request = (
        TripPlanningRequestDTO
        .model_validate(payload)
    )

    response = DayAssignmentSolver(
        exact_day_assignment_solver=(
            StubExactDayAssignmentSolver(
                make_success_result()
            )
        ),
        config=DayAssignmentSolverConfig(
            warn_when_stay_time_exceeds_available_time=False
        ),
    ).assign_pois_to_days(
        request=request,
        travel_time_matrices_by_day={
            1: {},
            2: {},
        },
    )

    assert response.warnings == []


# 정확 배정 결과에 알 수 없는 POI가 포함되면 거부
def test_rejects_unknown_poi_id_from_exact_result():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    result = ExactDayAssignmentResult(
        assigned_poi_ids_by_day=(
            MappingProxyType(
                {
                    1: ("unknown_poi",),
                    2: (),
                }
            )
        ),
        unassigned_poi_ids=(
            "poi_a",
            "poi_b",
        ),
        total_travel_minutes=0,
        evaluated_state_count=1,
    )

    with pytest.raises(
        ValueError,
        match="알 수 없는 poi_id",
    ):
        DayAssignmentSolver(
            exact_day_assignment_solver=(
                StubExactDayAssignmentSolver(
                    result
                )
            )
        ).assign_pois_to_days(
            request=request,
            travel_time_matrices_by_day={
                1: {},
                2: {},
            },
        )


# 동일한 POI가 여러 날짜에 배정되면 거부
def test_rejects_duplicate_assignment_across_days():
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    result = ExactDayAssignmentResult(
        assigned_poi_ids_by_day=(
            MappingProxyType(
                {
                    1: ("poi_a",),
                    2: ("poi_a",),
                }
            )
        ),
        unassigned_poi_ids=(
            "poi_b",
        ),
        total_travel_minutes=0,
        evaluated_state_count=1,
    )

    with pytest.raises(
        ValueError,
        match="여러 날짜에 중복 배정",
    ):
        DayAssignmentSolver(
            exact_day_assignment_solver=(
                StubExactDayAssignmentSolver(
                    result
                )
            )
        ).assign_pois_to_days(
            request=request,
            travel_time_matrices_by_day={
                1: {},
                2: {},
            },
        )
