# DayAssignmentSolver 단위 테스트
from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
    TripPlanningStatus,
)
from ai.route_planner.solvers.day_assignment_solver import DayAssignmentSolver


# 정상적인 TripPlanningRequestDTO 샘플을 생성하는 함수
def make_request_payload():
    return {
        "trip_id": "trip_001",
        "timezone": "Asia/Tokyo",
        "days": [
            {
                "day_index": 1,
                "date": "2026-08-01",
                "start_place": {
                    "place_id": "day1_start",
                    "name": "난바역",
                    "lat": 34.6657,
                    "lng": 135.5010,
                },
                "start_time": "10:00",
                "end_place": {
                    "place_id": "day1_end",
                    "name": "난바역",
                    "lat": 34.6657,
                    "lng": 135.5010,
                },
                "end_time": "20:00",
                "max_place_count": 3,
            },
            {
                "day_index": 2,
                "date": "2026-08-02",
                "start_place": {
                    "place_id": "day2_start",
                    "name": "우메다역",
                    "lat": 34.7025,
                    "lng": 135.4959,
                },
                "start_time": "09:00",
                "end_place": {
                    "place_id": "day2_end",
                    "name": "우메다역",
                    "lat": 34.7025,
                    "lng": 135.4959,
                },
                "end_time": "21:00",
                "max_place_count": 3,
            },
        ],
        "pois": [
            {
                "poi_id": "poi_001",
                "place_id": "google_place_001",
                "name": "도톤보리",
                "lat": 34.6686,
                "lng": 135.5030,
                "category": "TOURIST_ATTRACTION",
                "estimated_stay_minutes": 60,
                "priority": 1,
                "must_visit": True,
                "preferred_day_index": None,
            },
            {
                "poi_id": "poi_002",
                "place_id": "google_place_002",
                "name": "신사이바시",
                "lat": 34.6745,
                "lng": 135.5003,
                "category": "SHOPPING",
                "estimated_stay_minutes": 90,
                "priority": 2,
                "must_visit": True,
                "preferred_day_index": None,
            },
            {
                "poi_id": "poi_003",
                "place_id": "google_place_003",
                "name": "우메다 스카이빌딩",
                "lat": 34.7052,
                "lng": 135.4896,
                "category": "TOURIST_ATTRACTION",
                "estimated_stay_minutes": 60,
                "priority": 1,
                "must_visit": True,
                "preferred_day_index": None,
            },
            {
                "poi_id": "poi_004",
                "place_id": "google_place_004",
                "name": "그랜드 프론트 오사카",
                "lat": 34.7040,
                "lng": 135.4960,
                "category": "SHOPPING",
                "estimated_stay_minutes": 80,
                "priority": 2,
                "must_visit": True,
                "preferred_day_index": None,
            },
        ],
    }


# K-means 기반 day assignment가 POI를 day별로 배정하는지 검증
def test_assign_pois_to_days_with_kmeans_clusters():
    request = TripPlanningRequestDTO.model_validate(make_request_payload())
    solver = DayAssignmentSolver()

    response = solver.assign_pois_to_days(request)

    day1 = next(day_plan for day_plan in response.day_plans if day_plan.day_index == 1)
    day2 = next(day_plan for day_plan in response.day_plans if day_plan.day_index == 2)

    day1_names = {poi.name for poi in day1.assigned_pois}
    day2_names = {poi.name for poi in day2.assigned_pois}

    assert response.status == TripPlanningStatus.SUCCESS
    assert {"도톤보리", "신사이바시"}.issubset(day1_names)
    assert {"우메다 스카이빌딩", "그랜드 프론트 오사카"}.issubset(day2_names)


# preferred_day_index가 지정된 POI는 해당 day에 우선 배정되는지 검증
def test_assign_poi_to_preferred_day_first():
    payload = make_request_payload()
    payload["pois"][0]["preferred_day_index"] = 2

    request = TripPlanningRequestDTO.model_validate(payload)
    solver = DayAssignmentSolver()

    response = solver.assign_pois_to_days(request)

    day2 = next(day_plan for day_plan in response.day_plans if day_plan.day_index == 2)
    day2_names = {poi.name for poi in day2.assigned_pois}

    assert "도톤보리" in day2_names


# max_place_count를 초과하는 POI는 unassigned_pois로 분리되는지 검증
def test_unassign_poi_when_day_capacity_is_full():
    payload = make_request_payload()
    payload["days"][0]["max_place_count"] = 1
    payload["days"][1]["max_place_count"] = 1

    request = TripPlanningRequestDTO.model_validate(payload)
    solver = DayAssignmentSolver()

    response = solver.assign_pois_to_days(request)

    assert response.status == TripPlanningStatus.PARTIAL_SUCCESS
    assert len(response.unassigned_pois) == 2


# day별 estimated_total_stay_minutes가 배정된 POI의 체류 시간 합으로 계산되는지 검증
def test_estimated_total_stay_minutes_is_sum_of_assigned_pois():
    request = TripPlanningRequestDTO.model_validate(make_request_payload())
    solver = DayAssignmentSolver()

    response = solver.assign_pois_to_days(request)

    for day_plan in response.day_plans:
        expected_stay_minutes = sum(
            poi.estimated_stay_minutes
            for poi in day_plan.assigned_pois
        )

        assert day_plan.estimated_total_stay_minutes == expected_stay_minutes


# 체류 시간 합이 day 사용 가능 시간을 초과하면 warning을 반환하는지 검증
def test_warning_when_stay_time_exceeds_available_time():
    payload = make_request_payload()
    payload["days"][0]["start_time"] = "10:00"
    payload["days"][0]["end_time"] = "11:00"

    payload["pois"][0]["preferred_day_index"] = 1
    payload["pois"][1]["preferred_day_index"] = 1

    request = TripPlanningRequestDTO.model_validate(payload)
    solver = DayAssignmentSolver()

    response = solver.assign_pois_to_days(request)

    assert any("Day 1" in warning for warning in response.warnings)


# run_day_assignment 스크립트 함수가 응답 dict를 반환하는지 검증
def test_run_day_assignment_script_returns_response_dict():
    from ai.route_planner.scripts.run_day_assignment import run_day_assignment

    request = TripPlanningRequestDTO.model_validate(make_request_payload())

    response_payload = run_day_assignment(request)

    assert response_payload["trip_id"] == "trip_001"
    assert response_payload["status"] == "SUCCESS"
    assert len(response_payload["day_plans"]) == 2
    assert response_payload["unassigned_pois"] == []
