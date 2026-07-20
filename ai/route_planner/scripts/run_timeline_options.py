# TripPlanningRequest JSON을 읽어 DRIVE 기준 정확 일자 배정과 전체 Timeline 생성을 실행하는 CLI 스크립트
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from ai.route_planner.domain.schemas import (
    TravelMode,
)
from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)
from ai.route_planner.providers.google_routes_provider import (
    GoogleRoutesProvider,
)
from ai.route_planner.scripts.run_route_options_by_mode import (
    load_trip_planning_request,
)
from ai.route_planner.services.trip_planner_service import (
    TravelTimeMatrixProvider,
    TripPlannerService,
    TripPlannerServiceConfig,
)


# 여행 요청 전체 처리 Service를 실행하고 JSON 응답 반환
def run_timeline_options(
    request: TripPlanningRequestDTO,
    routes_provider: TravelTimeMatrixProvider | None = None,
) -> dict:
    service = TripPlannerService(
        routes_provider=(
            routes_provider
            or GoogleRoutesProvider()
        ),
        config=TripPlannerServiceConfig(
            day_assignment_travel_mode=(
                TravelMode.DRIVE
            ),
        ),
    )

    response = service.plan_trip(request)

    return response.model_dump(
        mode="json"
    )


# CLI 실행 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "TripPlanningRequest JSON을 읽어 DRIVE 기준 "
            "정확 일자 배정과 DRIVE, WALK, TRANSIT "
            "Route Option 및 Timeline을 생성합니다."
        )
    )

    parser.add_argument(
        "--json-path",
        required=True,
        help=(
            "TripPlanningRequest JSON 파일 경로입니다."
        ),
    )

    args = parser.parse_args()

    try:
        request = load_trip_planning_request(
            Path(args.json_path)
        )

        response_payload = (
            run_timeline_options(
                request=request,
            )
        )
    except ValidationError as error:
        print("[여행 일정 생성 실패]")
        print(
            "요청 JSON이 TripPlanningRequestDTO "
            "구조와 맞지 않습니다."
        )
        print(error)
        raise SystemExit(1)
    except (RuntimeError, ValueError) as error:
        print("[여행 일정 생성 실패]")
        print(error)
        raise SystemExit(1)

    print("[여행 일정 생성 성공]")
    print(
        json.dumps(
            response_payload,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
