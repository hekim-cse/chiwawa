# 선택한 이동 방식의 Matrix로 정확 일자 배정과 날짜별 Route Option 생성을 실행하는 CLI 스크립트
import argparse
import json
from pathlib import Path
from typing import List

from pydantic import ValidationError

from ai.route_planner.domain.schemas import (
    Location,
    TravelMode,
    TravelTimeElement,
)
from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    DayPlanDTO,
    PlaceDTO,
    PoiDTO,
    TripPlanningRequestDTO,
)
from ai.route_planner.providers.google_routes_provider import (
    GoogleRoutesProvider,
)
from ai.route_planner.services.trip_planner_service import (
    TravelTimeMatrixProvider,
)
from ai.route_planner.solvers.day_assignment_solver import (
    DayAssignmentSolver,
)
from ai.route_planner.solvers.exact_day_assignment_solver import (
    TravelTimeMatricesByDay,
)
from ai.route_planner.solvers.route_option_solver import (
    RouteOptionSolver,
)


# JSON 파일을 읽어 TripPlanningRequestDTO로 변환
def load_trip_planning_request(
    json_path: Path,
) -> TripPlanningRequestDTO:
    with json_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return TripPlanningRequestDTO.model_validate(
        payload
    )


# PlaceDTO를 Provider 요청용 Location으로 변환
def build_location_from_place(
    place: PlaceDTO,
) -> Location:
    return Location(
        name=place.place_id,
        lat=place.lat,
        lng=place.lng,
    )


# PoiDTO를 Provider 요청용 Location으로 변환
def build_location_from_poi(
    poi: PoiDTO,
) -> Location:
    return Location(
        name=poi.place_id,
        lat=poi.lat,
        lng=poi.lng,
    )


# 정확 일자 배정을 위해 날짜의 START, 전체 POI, END Location 생성
def build_assignment_locations(
    day: DayConstraintDTO,
    request: TripPlanningRequestDTO,
) -> List[Location]:
    locations = [
        build_location_from_place(
            day.start_place
        ),
        *[
            build_location_from_poi(poi)
            for poi in request.pois
        ],
        build_location_from_place(
            day.end_place
        ),
    ]

    validate_unique_location_names(
        locations=locations,
        context=(
            "정확 일자 배정 Matrix "
            f"day_index={day.day_index}"
        ),
    )

    return locations


# 배정 완료 DayPlan의 START, 배정 POI, END Location 생성
def build_locations_from_day_plan(
    day_plan: DayPlanDTO,
) -> List[Location]:
    locations = [
        build_location_from_place(
            day_plan.start_place
        ),
        *[
            build_location_from_poi(poi)
            for poi in day_plan.assigned_pois
        ],
        build_location_from_place(
            day_plan.end_place
        ),
    ]

    validate_unique_location_names(
        locations=locations,
        context=(
            "Route Option Matrix "
            f"day_index={day_plan.day_index}"
        ),
    )

    return locations


# 날짜별 정확 일자 배정 Matrix를 Provider에서 조회
def build_assignment_matrices_by_day(
    request: TripPlanningRequestDTO,
    travel_mode: TravelMode,
    routes_provider: TravelTimeMatrixProvider,
) -> TravelTimeMatricesByDay:
    matrices_by_day = {}

    for day in sorted(
        request.days,
        key=lambda item: item.day_index,
    ):
        locations = build_assignment_locations(
            day=day,
            request=request,
        )

        matrix_result = (
            routes_provider
            .build_travel_time_matrix_result(
                locations=locations,
                travel_mode=travel_mode,
            )
        )

        # 누락 구간에 가짜 비용을 추가하지 않고
        # Provider가 반환한 정상 Matrix만 정확 Solver에 전달
        matrices_by_day[day.day_index] = (
            matrix_result.matrix
        )

    return matrices_by_day


# Matrix key 충돌 방지를 위한 Location.name 중복 검증
def validate_unique_location_names(
    locations: List[Location],
    context: str,
) -> None:
    location_names = [
        location.name
        for location in locations
    ]

    if len(
        location_names
    ) != len(
        set(location_names)
    ):
        raise ValueError(
            f"{context}의 place_id는 "
            "모두 고유해야 합니다."
        )


# Provider 누락 구간을 JSON 출력용 dict로 변환
def dump_missing_element(
    element: TravelTimeElement,
) -> dict:
    return {
        "origin_name": element.origin_name,
        "destination_name": (
            element.destination_name
        ),
        "origin_index": element.origin_index,
        "destination_index": (
            element.destination_index
        ),
        "status": element.status,
        "condition": element.condition,
    }


# 선택한 이동 방식으로 정확 일자 배정과 Route Option 생성
def run_route_option_solver(
    request: TripPlanningRequestDTO,
    travel_mode: TravelMode,
    routes_provider: (
        TravelTimeMatrixProvider | None
    ) = None,
) -> dict:
    provider = (
        routes_provider
        or GoogleRoutesProvider()
    )

    assignment_matrices_by_day = (
        build_assignment_matrices_by_day(
            request=request,
            travel_mode=travel_mode,
            routes_provider=provider,
        )
    )

    trip_response = (
        DayAssignmentSolver()
        .assign_pois_to_days(
            request=request,
            travel_time_matrices_by_day=(
                assignment_matrices_by_day
            ),
        )
    )

    route_option_solver = RouteOptionSolver()
    route_options = []
    provider_missing_elements = []

    for day_plan in trip_response.day_plans:
        locations = (
            build_locations_from_day_plan(
                day_plan
            )
        )

        matrix_result = (
            provider
            .build_travel_time_matrix_result(
                locations=locations,
                travel_mode=travel_mode,
            )
        )

        provider_missing_elements.extend(
            dump_missing_element(element)
            for element
            in matrix_result.missing_elements
        )

        route_option = (
            route_option_solver
            .solve_route_option(
                day_plan=day_plan,
                travel_mode=travel_mode,
                travel_time_matrix=(
                    matrix_result.matrix
                ),
            )
        )

        route_options.append(
            route_option.model_dump(
                mode="json"
            )
        )

    return {
        "trip_id": request.trip_id,
        "travel_mode": travel_mode.value,
        "route_options": route_options,
        "provider_missing_elements": (
            provider_missing_elements
        ),
    }


# CLI 실행 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "TripPlanningRequest JSON을 읽어 선택한 "
            "이동 방식 기준 정확 일자 배정과 "
            "날짜별 Route Option을 생성합니다."
        )
    )

    parser.add_argument(
        "--json-path",
        required=True,
        help=(
            "TripPlanningRequest JSON 파일 "
            "경로입니다."
        ),
    )

    parser.add_argument(
        "--travel-mode",
        default=TravelMode.DRIVE.value,
        choices=[
            mode.value
            for mode in TravelMode
        ],
        help=(
            "정확 일자 배정과 Route Option에 "
            "사용할 이동 방식입니다."
        ),
    )

    args = parser.parse_args()

    try:
        request = load_trip_planning_request(
            Path(args.json_path)
        )

        response_payload = (
            run_route_option_solver(
                request=request,
                travel_mode=TravelMode(
                    args.travel_mode
                ),
            )
        )
    except ValidationError as error:
        print("[Route Option Solver 실패]")
        print(
            "요청 JSON이 "
            "TripPlanningRequestDTO 구조와 "
            "맞지 않습니다."
        )
        print(error)
        raise SystemExit(1)
    except (RuntimeError, ValueError) as error:
        print("[Route Option Solver 실패]")
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
