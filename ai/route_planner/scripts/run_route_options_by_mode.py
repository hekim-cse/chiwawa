# DRIVE 기준 정확 일자 배정 후 모든 이동 방식의 Route Option을 생성하는 CLI 스크립트
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
    DayConstraintDTO,
    DayPlanDTO,
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
from ai.route_planner.solvers.route_options_by_mode_solver import (
    RouteOptionsByModeSolver,
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


# 정확 일자 배정을 위해 날짜의 START, 전체 POI, END Location 생성
def build_assignment_locations(
    day: DayConstraintDTO,
    request: TripPlanningRequestDTO,
) -> List[Location]:
    locations = [
        Location(
            name=day.start_place.place_id,
            lat=day.start_place.lat,
            lng=day.start_place.lng,
        ),
        *[
            Location(
                name=poi.place_id,
                lat=poi.lat,
                lng=poi.lng,
            )
            for poi in request.pois
        ],
        Location(
            name=day.end_place.place_id,
            lat=day.end_place.lat,
            lng=day.end_place.lng,
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


# 배정 완료 DayPlan을 Route Option용 Location 목록으로 변환
def build_locations_from_day_plan(
    day_plan: DayPlanDTO,
) -> List[Location]:
    locations = [
        Location(
            name=(
                day_plan
                .start_place.place_id
            ),
            lat=day_plan.start_place.lat,
            lng=day_plan.start_place.lng,
        ),
        *[
            Location(
                name=poi.place_id,
                lat=poi.lat,
                lng=poi.lng,
            )
            for poi
            in day_plan.assigned_pois
        ],
        Location(
            name=day_plan.end_place.place_id,
            lat=day_plan.end_place.lat,
            lng=day_plan.end_place.lng,
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


# DRIVE 기준 날짜별 정확 일자 배정 Matrix 조회
def build_assignment_matrices_by_day(
    request: TripPlanningRequestDTO,
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
                travel_mode=TravelMode.DRIVE,
            )
        )

        # 누락 구간을 임의 비용으로 보충하지 않고
        # 정상 계산된 Matrix만 정확 Solver에 전달
        matrices_by_day[day.day_index] = (
            matrix_result.matrix
        )

    return matrices_by_day


# 하나의 날짜에 대해 이동 방식별 Matrix 결과 생성
def build_matrix_results_by_mode(
    day_plan: DayPlanDTO,
    routes_provider: TravelTimeMatrixProvider,
) -> Dict[
    TravelMode,
    TravelTimeMatrixResult,
]:
    locations = (
        build_locations_from_day_plan(
            day_plan
        )
    )

    return {
        travel_mode: (
            routes_provider
            .build_travel_time_matrix_result(
                locations=locations,
                travel_mode=travel_mode,
            )
        )
        for travel_mode in (
            TravelMode.DRIVE,
            TravelMode.WALK,
            TravelMode.TRANSIT,
        )
    }


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


# DRIVE 정확 일자 배정 후 이동 방식별 Route Option 생성
def run_route_options_by_mode(
    request: TripPlanningRequestDTO,
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

    route_options_solver = (
        RouteOptionsByModeSolver()
    )
    updated_day_plans = []

    for day_plan in trip_response.day_plans:
        matrix_results_by_mode = (
            build_matrix_results_by_mode(
                day_plan=day_plan,
                routes_provider=provider,
            )
        )

        updated_day_plan = (
            route_options_solver
            .assign_route_options(
                day_plan=day_plan,
                matrix_results_by_mode=(
                    matrix_results_by_mode
                ),
            )
        )

        updated_day_plans.append(
            updated_day_plan
        )

    updated_trip_response = (
        trip_response.model_copy(
            update={
                "day_plans": updated_day_plans,
            }
        )
    )

    return updated_trip_response.model_dump(
        mode="json"
    )


# CLI 실행 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "TripPlanningRequest JSON을 읽어 "
            "DRIVE 기준 정확 일자 배정 후 "
            "DRIVE, WALK, TRANSIT "
            "Route Option을 생성합니다."
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

    args = parser.parse_args()

    try:
        request = load_trip_planning_request(
            Path(args.json_path)
        )

        response_payload = (
            run_route_options_by_mode(
                request=request,
            )
        )
    except ValidationError as error:
        print(
            "[이동 방식별 Route Option "
            "생성 실패]"
        )
        print(
            "요청 JSON이 "
            "TripPlanningRequestDTO 구조와 "
            "맞지 않습니다."
        )
        print(error)
        raise SystemExit(1)
    except (RuntimeError, ValueError) as error:
        print(
            "[이동 방식별 Route Option "
            "생성 실패]"
        )
        print(error)
        raise SystemExit(1)

    print(
        "[이동 방식별 Route Option 생성 성공]"
    )
    print(
        json.dumps(
            response_payload,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
