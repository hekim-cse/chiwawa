# TripPlanningRequest JSON을 읽어 모든 이동 방식의 Route Option을 생성하는 실행 스크립트
import argparse
import json
from pathlib import Path
from typing import Dict, List

from pydantic import ValidationError

from ai.route_planner.domain.schemas import (
    Location,
    TravelMode,
    TravelTimeMatrixResult,
)
from ai.route_planner.domain.trip_schemas import (
    DayPlanDTO,
    TripPlanningRequestDTO,
)
from ai.route_planner.providers.google_routes_provider import GoogleRoutesProvider
from ai.route_planner.solvers.day_assignment_solver import DayAssignmentSolver
from ai.route_planner.solvers.route_options_by_mode_solver import (
    RouteOptionsByModeSolver,
)


# JSON 파일을 읽어 TripPlanningRequestDTO로 변환하는 함수
def load_trip_planning_request(
    json_path: Path,
) -> TripPlanningRequestDTO:
    with json_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return TripPlanningRequestDTO.model_validate(payload)


# DayPlanDTO의 출발지, POI, 도착지를 Google Routes API 요청용 Location으로 변환하는 함수
# Location.name에는 RouteOptionSolver의 matrix key와 동일한 place_id를 저장
def build_locations_from_day_plan(
    day_plan: DayPlanDTO,
) -> List[Location]:
    return [
        Location(   
            name=day_plan.start_place.place_id,
            lat=day_plan.start_place.lat,
            lng=day_plan.start_place.lng,
        ),
        *[
            Location(  
                name=poi.place_id,
                lat=poi.lat,
                lng=poi.lng,
            )
            for poi in day_plan.assigned_pois
        ],
        Location(
            name=day_plan.end_place.place_id,
            lat=day_plan.end_place.lat,
            lng=day_plan.end_place.lng,
        ),
    ]


# 하나의 day에 대해 이동 방식별 실제 Google TravelTimeMatrixResult를 생성하는 함수
def build_matrix_results_by_mode(
    day_plan: DayPlanDTO,
    routes_provider: GoogleRoutesProvider,
) -> Dict[TravelMode, TravelTimeMatrixResult]:
    locations = build_locations_from_day_plan(day_plan)

    return {
        travel_mode: routes_provider.build_travel_time_matrix_result(
            locations=locations,
            travel_mode=travel_mode,
        )
        for travel_mode in (
            TravelMode.DRIVE,
            TravelMode.WALK,
            TravelMode.TRANSIT,
        )
    }


# 여행 요청에 대해 day assignment와 이동 방식별 route option 생성을 실행하는 함수
def run_route_options_by_mode(
    request: TripPlanningRequestDTO,
    routes_provider: GoogleRoutesProvider | None = None,
) -> dict:
    day_assignment_solver = DayAssignmentSolver()
    route_options_solver = RouteOptionsByModeSolver()
    routes_provider = routes_provider or GoogleRoutesProvider()

    trip_response = day_assignment_solver.assign_pois_to_days(request)

    day_plans_with_route_options = []

    for day_plan in trip_response.day_plans:
        matrix_results_by_mode = build_matrix_results_by_mode(
            day_plan=day_plan,
            routes_provider=routes_provider,
        )

        updated_day_plan = route_options_solver.assign_route_options(
            day_plan=day_plan,
            matrix_results_by_mode=matrix_results_by_mode,
        )

        day_plans_with_route_options.append(updated_day_plan)

    updated_trip_response = trip_response.model_copy(
        update={
            "day_plans": day_plans_with_route_options,
        }
    )

    return updated_trip_response.model_dump(mode="json")


# 스크립트 실행 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "TripPlanningRequest JSON을 읽어 DRIVE, WALK, TRANSIT "
            "Route Option을 생성합니다."
        )
    )

    parser.add_argument(
        "--json-path",
        required=True,
        help="TripPlanningRequest JSON 파일 경로입니다.",
    )

    args = parser.parse_args()

    try:
        request = load_trip_planning_request(
            Path(args.json_path)
        )

        response_payload = run_route_options_by_mode(
            request=request,
        )
    except ValidationError as error:
        print("[이동 방식별 Route Option 생성 실패]")
        print("요청 JSON이 TripPlanningRequestDTO 구조와 맞지 않습니다.")
        print(error)
        raise SystemExit(1)
    except (RuntimeError, ValueError) as error:
        print("[이동 방식별 Route Option 생성 실패]")
        print(error)
        raise SystemExit(1)

    print("[이동 방식별 Route Option 생성 성공]")
    print(
        json.dumps(
            response_payload,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
