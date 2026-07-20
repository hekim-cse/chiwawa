# 요청과 날짜별 명시적 Matrix JSON을 읽어 정확 일자 배정 결과를 출력하는 CLI 스크립트
import argparse
import json
from pathlib import Path
from typing import Dict

from pydantic import BaseModel, ValidationError

from ai.route_planner.domain.schemas import (
    TravelTimeMatrix,
)
from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)
from ai.route_planner.evaluation.schemas import (
    DayTravelTimeMatrixDTO,
)
from ai.route_planner.solvers.day_assignment_solver import (
    DayAssignmentSolver,
)


# 정확 일자 배정 실행 입력 DTO
class DayAssignmentInputDTO(BaseModel):
    request: TripPlanningRequestDTO
    travel_time_entries_by_day: list[
        DayTravelTimeMatrixDTO
    ]


# JSON 파일을 읽어 정확 일자 배정 입력 DTO로 변환
def load_day_assignment_input(
    json_path: Path,
) -> DayAssignmentInputDTO:
    with json_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return DayAssignmentInputDTO.model_validate(
        payload
    )


# 날짜별 JSON Matrix Entry를 tuple key Matrix Map으로 변환
def build_travel_time_matrices_by_day(
    input_dto: DayAssignmentInputDTO,
) -> Dict[int, TravelTimeMatrix]:
    matrices_by_day: Dict[
        int,
        TravelTimeMatrix,
    ] = {}

    for day_matrix in (
        input_dto.travel_time_entries_by_day
    ):
        if (
            day_matrix.day_index
            in matrices_by_day
        ):
            raise ValueError(
                "Duplicated day matrix: "
                f"day_index={day_matrix.day_index}"
            )

        matrix: TravelTimeMatrix = {}

        for entry in day_matrix.entries:
            key = (
                entry.origin_place_id,
                entry.destination_place_id,
            )

            if key in matrix:
                raise ValueError(
                    "Duplicated travel time entry: "
                    f"day_index="
                    f"{day_matrix.day_index}, "
                    f"{entry.origin_place_id} -> "
                    f"{entry.destination_place_id}"
                )

            matrix[key] = (
                entry.travel_minutes
            )

        matrices_by_day[
            day_matrix.day_index
        ] = matrix

    expected_day_indexes = {
        day.day_index
        for day in input_dto.request.days
    }
    actual_day_indexes = set(
        matrices_by_day
    )

    if (
        actual_day_indexes
        != expected_day_indexes
    ):
        raise ValueError(
            "날짜별 Matrix의 day_index 집합이 "
            "request.days와 일치해야 합니다: "
            f"expected="
            f"{sorted(expected_day_indexes)}, "
            f"actual="
            f"{sorted(actual_day_indexes)}"
        )

    return matrices_by_day


# 명시적 날짜별 Matrix로 정확 일자 배정 실행
def run_day_assignment(
    input_dto: DayAssignmentInputDTO,
) -> dict:
    matrices_by_day = (
        build_travel_time_matrices_by_day(
            input_dto
        )
    )

    response = (
        DayAssignmentSolver()
        .assign_pois_to_days(
            request=input_dto.request,
            travel_time_matrices_by_day=(
                matrices_by_day
            ),
        )
    )

    return response.model_dump(
        mode="json"
    )


# CLI 실행 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "요청과 날짜별 명시적 Matrix JSON을 "
            "읽어 정확 일자 배정 결과를 출력합니다."
        )
    )

    parser.add_argument(
        "--json-path",
        required=True,
        help=(
            "Day Assignment 입력 JSON "
            "파일 경로입니다."
        ),
    )

    args = parser.parse_args()

    try:
        input_dto = load_day_assignment_input(
            Path(args.json_path)
        )

        response_payload = (
            run_day_assignment(
                input_dto
            )
        )
    except (
        ValidationError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        print("[Day Assignment 실패]")
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
