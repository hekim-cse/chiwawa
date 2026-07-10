# TripPlanningRequest JSON 파일을 읽어 DayAssignmentSolver 실행 결과를 출력하는 스크립트
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from ai.route_planner.domain.trip_schemas import TripPlanningRequestDTO
from ai.route_planner.solvers.day_assignment_solver import DayAssignmentSolver


# JSON 파일을 읽어 TripPlanningRequestDTO로 변환하는 함수
def load_trip_planning_request(json_path: Path) -> TripPlanningRequestDTO:
    with json_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return TripPlanningRequestDTO.model_validate(payload)


# TripPlanningRequestDTO를 기반으로 day별 POI 배정 결과를 생성하는 함수
def run_day_assignment(request: TripPlanningRequestDTO) -> dict:
    solver = DayAssignmentSolver()
    response = solver.assign_pois_to_days(request)

    return response.model_dump(mode="json")


# 스크립트 실행 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description="TripPlanningRequest JSON 파일을 읽어 day별 POI 배정 결과를 출력합니다."
    )

    parser.add_argument(
        "--json-path",
        required=True,
        help="Day Assignment를 실행할 TripPlanningRequest JSON 파일 경로입니다.",
    )

    args = parser.parse_args()

    try:
        request = load_trip_planning_request(Path(args.json_path))
        response_payload = run_day_assignment(request)
    except ValidationError as error:
        print("[Day Assignment 실패]")
        print("요청 JSON이 TripPlanningRequestDTO 구조와 맞지 않습니다.")
        print(error)
        raise SystemExit(1)

    print("[Day Assignment 성공]")
    print(
        json.dumps(
            response_payload,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
