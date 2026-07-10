# RouteOptionSolver 단위 테스트
from ai.route_planner.domain.schemas import TravelMode
from ai.route_planner.domain.trip_schemas import DayPlanDTO, TripPlanningRequestDTO
from ai.route_planner.solvers.day_assignment_solver import DayAssignmentSolver
from ai.route_planner.solvers.route_option_solver import RouteOptionSolver


# RouteOptionSolver 테스트용 TripPlanningRequest payload 생성 함수
def make_request_payload():
    return {
        "trip_id": "trip_route_001",
        "timezone": "Asia/Tokyo",
        "days": [
            {
                "day_index": 1,
                "date": "2026-08-01",
                "start_place": {
                    "place_id": "start",
                    "name": "출발지",
                    "lat": 34.6657,
                    "lng": 135.5010,
                },
                "start_time": "10:00",
                "end_place": {
                    "place_id": "end",
                    "name": "도착지",
                    "lat": 34.7052,
                    "lng": 135.4896,
                },
                "end_time": "20:00",
                "max_place_count": 4,
            }
        ],
        "pois": [
            {
                "poi_id": "poi_001",
                "place_id": "a",
                "name": "A 장소",
                "lat": 34.6700,
                "lng": 135.5020,
                "category": "TOURIST_ATTRACTION",
                "estimated_stay_minutes": 60,
                "priority": 1,
                "must_visit": True,
                "preferred_day_index": 1,
            },
            {
                "poi_id": "poi_002",
                "place_id": "b",
                "name": "B 장소",
                "lat": 34.6800,
                "lng": 135.5000,
                "category": "CAFE",
                "estimated_stay_minutes": 40,
                "priority": 2,
                "must_visit": True,
                "preferred_day_index": 1,
            },
            {
                "poi_id": "poi_003",
                "place_id": "c",
                "name": "C 장소",
                "lat": 34.6900,
                "lng": 135.4950,
                "category": "SHOPPING",
                "estimated_stay_minutes": 50,
                "priority": 2,
                "must_visit": True,
                "preferred_day_index": 1,
            },
        ],
    }


# 테스트용 DayPlanDTO 생성 함수
def make_day_plan() -> DayPlanDTO:
    request = TripPlanningRequestDTO.model_validate(make_request_payload())
    response = DayAssignmentSolver().assign_pois_to_days(request)

    return response.day_plans[0]


# 정상 이동 시간 행렬 생성 함수
def make_travel_time_matrix():
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


# Cheapest Insertion과 Local Search를 통해 경로 옵션을 생성하는지 검증
def test_solve_route_option_returns_ordered_route():
    day_plan = make_day_plan()
    solver = RouteOptionSolver()

    route_option = solver.solve_route_option(
        day_plan=day_plan,
        travel_mode=TravelMode.DRIVE,
        travel_time_matrix=make_travel_time_matrix(),
    )

    ordered_place_ids = [
        stop.place_id
        for stop in route_option.ordered_stops
    ]

    assert route_option.day_index == 1
    assert route_option.travel_mode == TravelMode.DRIVE
    assert ordered_place_ids[0] == "start"
    assert ordered_place_ids[-1] == "end"
    assert set(ordered_place_ids[1:-1]) == {"a", "b", "c"}
    assert route_option.total_travel_minutes == 40
    assert route_option.missing_segments == []
    assert route_option.warnings == []


# RouteLegDTO가 방문 순서에 맞게 생성되는지 검증
def test_solve_route_option_builds_route_legs():
    day_plan = make_day_plan()
    solver = RouteOptionSolver()

    route_option = solver.solve_route_option(
        day_plan=day_plan,
        travel_mode=TravelMode.DRIVE,
        travel_time_matrix=make_travel_time_matrix(),
    )

    assert len(route_option.route_legs) == 4
    assert route_option.route_legs[0].origin_place_id == "start"
    assert route_option.route_legs[-1].destination_place_id == "end"


# 이동 시간 정보가 부족한 POI는 warning과 missing_segments로 추적되는지 검증
def test_solve_route_option_tracks_missing_segments():
    day_plan = make_day_plan()
    solver = RouteOptionSolver()

    travel_time_matrix = {
        ("start", "a"): 10,
        ("a", "end"): 10,
    }

    route_option = solver.solve_route_option(
        day_plan=day_plan,
        travel_mode=TravelMode.DRIVE,
        travel_time_matrix=travel_time_matrix,
    )

    ordered_place_ids = [
        stop.place_id
        for stop in route_option.ordered_stops
    ]

    assert ordered_place_ids == ["start", "a", "end"]
    assert route_option.total_travel_minutes == 20
    assert route_option.missing_segments
    assert route_option.warnings


# assigned_pois가 비어 있어도 start에서 end로 이어지는 route option을 생성하는지 검증
def test_solve_route_option_handles_empty_assigned_pois():
    day_plan = make_day_plan().model_copy(update={"assigned_pois": []})
    solver = RouteOptionSolver()

    route_option = solver.solve_route_option(
        day_plan=day_plan,
        travel_mode=TravelMode.WALK,
        travel_time_matrix={
            ("start", "end"): 25,
        },
    )

    ordered_place_ids = [
        stop.place_id
        for stop in route_option.ordered_stops
    ]

    assert ordered_place_ids == ["start", "end"]
    assert route_option.total_travel_minutes == 25
    assert len(route_option.route_legs) == 1
    assert route_option.warnings == []


# run_route_option_solver 스크립트 함수가 GoogleRoutesProvider 인터페이스 기반으로 route option 결과를 반환하는지 검증
def test_run_route_option_solver_script_returns_response_dict_with_fake_provider():
    from ai.route_planner.domain.schemas import TravelTimeMatrixResult
    from ai.route_planner.scripts.run_route_option_solver import run_route_option_solver

    class FakeGoogleRoutesProvider:
        def build_travel_time_matrix_result(self, locations, travel_mode):
            place_ids = [
                location.name
                for location in locations
            ]

            matrix = {}

            for origin in place_ids:
                for destination in place_ids:
                    if origin == destination:
                        continue

                    matrix[(origin, destination)] = 10

            return TravelTimeMatrixResult(
                matrix=matrix,
                missing_elements=[],
            )

    request = TripPlanningRequestDTO.model_validate(make_request_payload())

    response_payload = run_route_option_solver(
        request=request,
        travel_mode=TravelMode.DRIVE,
        routes_provider=FakeGoogleRoutesProvider(),
    )

    assert response_payload["trip_id"] == "trip_route_001"
    assert response_payload["travel_mode"] == "DRIVE"
    assert len(response_payload["route_options"]) == 1
    assert response_payload["provider_missing_elements"] == []

    route_option = response_payload["route_options"][0]

    assert route_option["day_index"] == 1
    assert route_option["travel_mode"] == "DRIVE"
    assert route_option["ordered_stops"][0]["stop_type"] == "START"
    assert route_option["ordered_stops"][-1]["stop_type"] == "END"
