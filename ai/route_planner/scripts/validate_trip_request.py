# TripPlanningRequest JSON 파일을 읽어 DTO 검증을 수행하는 실행 스크립트
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from ai.route_planner.domain.trip_schemas import TripPlanningRequestDTO


# JSON 파일을 읽어 TripPlanningRequestDTO로 변환하는 함수
def validate_trip_request(json_path: Path) -> TripPlanningRequestDTO:
    with json_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return TripPlanningRequestDTO.model_validate(payload)


# 스크립트 실행 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description="TripPlanningRequest JSON 파일이 AI DTO 구조와 맞는지 검증합니다."
    )

    parser.add_argument(
        "--json-path",
        required=True,
        help="검증할 TripPlanningRequest JSON 파일 경로입니다.",
    )

    args = parser.parse_args()

    try:
        request = validate_trip_request(Path(args.json_path))
    except ValidationError as error:
        print("[검증 실패]")
        print(error)
        raise SystemExit(1)

    print("[검증 성공]")
    print(f"trip_id: {request.trip_id}")
    print(f"timezone: {request.timezone}")
    print(f"days: {len(request.days)}개")
    print(f"pois: {len(request.pois)}개")


if __name__ == "__main__":
    main()
