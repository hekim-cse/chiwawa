# TripPlanningRequest JSON 파일을 읽어 실제 Google Routes Provider 기반 Route Option Solver 결과를 출력하는 스크립트
import argparse
import json
from pathlib import Path
from typing import List

from pydantic import ValidationError

from ai.route_planner.domain.schemas import Location, TravelMode, TravelTimeElement
from ai.route_planner.domain.trip_schemas import (
    DayPlanDTO,
    PlaceDTO,
    PoiDTO,
    TripPlanningRequestDTO,
)
from ai.route_planner.providers.google_routes_provider import GoogleRoutesProvider
from ai.route_planner.solvers.day_assignment_solver import DayAssignmentSolver
from ai.route_planner.solvers.route_option_solver import RouteOptionSolver


# JSON 파일을 읽어 TripPlanningRequestDTO로 변환하는 함수
def load_trip_planning_request(json_path: Path) -> TripPlanningRequestDTO:
    with json_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return TripPlanningRequestDTO.model_validate(payload)


# PlaceDTO를 GoogleRoutesProvider가 사용할 Location으로 변환하는 함수
# Location.name에는 실제 장소명이 아니라 place_id를 넣어 RouteOptionSolver의 matrix key와 맞춘다.
def build_location_from_place(place: PlaceDTO) -> Location:
    return Location(
        name=place.place_id,
        lat=place.lat,
        lng=place.lng,
    )


# PoiDTO를 GoogleRoutesProvider가 사용할 Location으로 변환하는 함수
# Location.name에는 poi_id가 아니라 place_id를 넣는다.
def build_location_from_poi(poi: PoiDTO) -> Location:
    return Location(
        name=poi.place_id,
        lat=poi.lat,
        lng=poi.lng,
    )


# DayPlanDTO에 포함된 start, assigned_pois, end를 Google Routes API 요청용 Location 목록으로 변환하는 함수
def build_locations_from_day_plan(day_plan: DayPlanDTO) -> List[Location]:
    return [
        build_location_from_place(day_plan.start_place),
        *[
            build_location_from_poi(poi)
            for poi in day_plan.assigned_pois
        ],
        build_location_from_place(day_plan.end_place),
    ]


# Google Routes Provider에서 반환한 missing element를 출력 가능한 dict로 변환하는 함수
def dump_missing_element(element: TravelTimeElement) -> dict:
    return {
        "origin_name": element.origin_name,
        "destination_name": element.destination_name,
        "origin_index": element.origin_index,
        "destination_index": element.destination_index,
        "status": element.status,
        "condition": element.condition,
    }


# TripPlanningRequestDTO를 기반으로 Day Assignment와 실제 Google Routes 기반 Route Option Solver를 실행하는 함수
def run_route_option_solver(
    request: TripPlanningRequestDTO,
    travel_mode: TravelMode,
    routes_provider: GoogleRoutesProvider | None = None,
) -> dict:
    day_assignment_solver = DayAssignmentSolver()
    route_option_solver = RouteOptionSolver()
    routes_provider = routes_provider or GoogleRoutesProvider()

    trip_response = day_assignment_solver.assign_pois_to_days(request)

    route_options = []
    provider_missing_elements = []

    for day_plan in trip_response.day_plans:
        locations = build_locations_from_day_plan(day_plan)

        travel_time_matrix_result = routes_provider.build_travel_time_matrix_result(
            locations=locations,
            travel_mode=travel_mode,
        )

        provider_missing_elements.extend(
            dump_missing_element(element)
            for element in travel_time_matrix_result.missing_elements
        )

        route_option = route_option_solver.solve_route_option(
            day_plan=day_plan,
            travel_mode=travel_mode,
            travel_time_matrix=travel_time_matrix_result.matrix,
        )

        route_options.append(route_option.model_dump(mode="json"))

    return {
        "trip_id": request.trip_id,
        "travel_mode": travel_mode.value,
        "route_options": route_options,
        "provider_missing_elements": provider_missing_elements,
    }


# 스크립트 실행 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description="TripPlanningRequest JSON 파일을 읽어 실제 Google Routes 기반 day별 Route Option 결과를 출력합니다."
    )

    parser.add_argument(
        "--json-path",
        required=True,
        help="Route Option Solver를 실행할 TripPlanningRequest JSON 파일 경로입니다.",
    )

    parser.add_argument(
        "--travel-mode",
        default=TravelMode.DRIVE.value,
        choices=[mode.value for mode in TravelMode],
        help="Route Option을 생성할 이동 방식입니다.",
    )

    args = parser.parse_args()

    try:
        request = load_trip_planning_request(Path(args.json_path))
        response_payload = run_route_option_solver(
            request=request,
            travel_mode=TravelMode(args.travel_mode),
        )
    except ValidationError as error:
        print("[Route Option Solver 실패]")
        print("요청 JSON이 TripPlanningRequestDTO 구조와 맞지 않습니다.")
        print(error)
        raise SystemExit(1)

    print("[Route Option Solver 성공]")
    print(
        json.dumps(
            response_payload,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
