# TripPlanningRequest JSON을 읽어 이동 방식별 Route Option과 Timeline을 생성하는 실행 스크립트
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    TripPlanningRequestDTO,
)
from ai.route_planner.providers.google_routes_provider import (
    GoogleRoutesProvider,
)
from ai.route_planner.scripts.run_route_options_by_mode import (
    build_matrix_results_by_mode,
    load_trip_planning_request,
)
from ai.route_planner.solvers.day_assignment_solver import (
    DayAssignmentSolver,
)
from ai.route_planner.solvers.route_options_by_mode_solver import (
    RouteOptionsByModeSolver,
)
from ai.route_planner.solvers.timeline_options_builder import (
    TimelineOptionsBuilder,
)


# day_index를 key로 하는 DayConstraintDTO 조회 맵을 생성하는 함수
def build_day_constraints_by_index(
    request: TripPlanningRequestDTO,
) -> dict[int, DayConstraintDTO]:
    return {
        day_constraint.day_index: day_constraint
        for day_constraint in request.days
    }


# 여행 요청에 대해 day assignment, 이동 방식별 route option, timeline 생성을 실행하는 함수
def run_timeline_options(
    request: TripPlanningRequestDTO,
    routes_provider: GoogleRoutesProvider | None = None,
) -> dict:
    day_assignment_solver = DayAssignmentSolver()
    route_options_solver = RouteOptionsByModeSolver()
    timeline_options_builder = TimelineOptionsBuilder()
    routes_provider = routes_provider or GoogleRoutesProvider()

    # day assignment를 수행하여 각 day에 POI를 배정하고, day_index를 key로 하는 DayConstraintDTO 조회 맵을 생성
    trip_response = day_assignment_solver.assign_pois_to_days(
        request
    )

    # day_index를 key로 하는 DayConstraintDTO 조회 맵 생성
    day_constraints_by_index = build_day_constraints_by_index(
        request
    )

    # 각 day_plan에 대해 이동 방식별 route option과 timeline을 생성하고, 최종 trip_response를 갱신
    day_plans_with_timelines = []

    for day_plan in trip_response.day_plans:
        day_constraint = day_constraints_by_index.get(
            day_plan.day_index
        )

        if day_constraint is None:
            raise ValueError(
                "DayConstraintDTO not found for day_index: "
                f"{day_plan.day_index}"
            )

        # 이동 방식별 route option을 생성하기 위해 Google Directions API를 호출하고, route option을 갱신
        matrix_results_by_mode = build_matrix_results_by_mode(
            day_plan=day_plan,
            routes_provider=routes_provider,
        )

        # 이동 방식별 route option을 생성하고, 누락 구간이 있는 옵션은 warning만 추가
        day_plan_with_route_options = (
            route_options_solver.assign_route_options(
                day_plan=day_plan,
                matrix_results_by_mode=matrix_results_by_mode,
            )
        )

        # 각 이동 방식별 route option에 대해 timeline을 생성하거나 누락 상태를 반영하고, day_plan을 갱신
        day_plan_with_timelines = (
            timeline_options_builder.assign_timelines(
                day_constraint=day_constraint,
                day_plan=day_plan_with_route_options,
            )
        )

        # 갱신된 day_plan을 최종 trip_response에 추가
        day_plans_with_timelines.append(
            day_plan_with_timelines
        )

    updated_trip_response = trip_response.model_copy(
        update={
            "day_plans": day_plans_with_timelines,
        }
    )

    return updated_trip_response.model_dump(
        mode="json"
    )


# 스크립트 실행 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "TripPlanningRequest JSON을 읽어 DRIVE, WALK, TRANSIT "
            "Route Option과 Timeline을 생성합니다."
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

        response_payload = run_timeline_options(
            request=request,
        )
    except ValidationError as error:
        print("[이동 방식별 Timeline 생성 실패]")
        print(
            "요청 JSON이 TripPlanningRequestDTO 구조와 "
            "맞지 않습니다."
        )
        print(error)
        raise SystemExit(1)
    except (RuntimeError, ValueError) as error:
        print("[이동 방식별 Timeline 생성 실패]")
        print(error)
        raise SystemExit(1)

    print("[이동 방식별 Timeline 생성 성공]")
    print(
        json.dumps(
            response_payload,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
