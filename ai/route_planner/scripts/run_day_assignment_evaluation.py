# 명시적 날짜별 Matrix Fixture로 정확 일자 배정 평가를 실행하고 결과를 저장하는 CLI 스크립트
import argparse
import json
from pathlib import Path
from typing import Any, Dict

from pydantic import ValidationError

from ai.route_planner.domain.schemas import (
    TravelTimeMatrix,
)
from ai.route_planner.evaluation.day_assignment_evaluator import (
    DayAssignmentEvaluator,
)
from ai.route_planner.evaluation.schemas import (
    DayAssignmentEvaluationScenarioDTO,
)


# JSON Fixture를 정확 일자 배정 평가 Scenario로 변환
def load_day_assignment_evaluation_scenario(
    fixture_path: Path,
) -> DayAssignmentEvaluationScenarioDTO:
    with fixture_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return (
        DayAssignmentEvaluationScenarioDTO
        .model_validate(payload)
    )


# 날짜별 JSON Matrix Entry를 tuple key Matrix Map으로 변환
def build_travel_time_matrices_by_day(
    scenario: DayAssignmentEvaluationScenarioDTO,
) -> Dict[int, TravelTimeMatrix]:
    matrices_by_day: Dict[
        int,
        TravelTimeMatrix,
    ] = {}

    for day_matrix in (
        scenario.travel_time_entries_by_day
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
        for day in scenario.request.days
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


# 정확 일자 배정 평가 실행
def run_day_assignment_evaluation(
    scenario: DayAssignmentEvaluationScenarioDTO,
) -> Dict[str, Any]:
    matrices_by_day = (
        build_travel_time_matrices_by_day(
            scenario
        )
    )

    result = DayAssignmentEvaluator().evaluate(
        scenario_id=scenario.scenario_id,
        request=scenario.request,
        travel_time_matrices_by_day=(
            matrices_by_day
        ),
    )

    return result.model_dump(
        mode="json"
    )


# 평가 결과 JSON 파일 저장
def save_day_assignment_evaluation_result(
    result_payload: Dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            result_payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# CLI 인자 파싱
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "명시적 Matrix 기반 정확 "
            "일자 배정 평가 실행"
        )
    )

    parser.add_argument(
        "--fixture-path",
        type=Path,
        required=True,
        help=(
            "정확 일자 배정 평가 "
            "Scenario JSON 경로"
        ),
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        required=False,
        help=(
            "정확 일자 배정 평가 결과 "
            "JSON 저장 경로"
        ),
    )

    return parser.parse_args()


# CLI Entrypoint
def main() -> None:
    args = parse_args()

    try:
        scenario = (
            load_day_assignment_evaluation_scenario(
                args.fixture_path
            )
        )
        result_payload = (
            run_day_assignment_evaluation(
                scenario
            )
        )
    except (
        ValidationError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        print(
            "[Day Assignment Evaluation 실패]"
        )
        print(error)
        raise SystemExit(1)

    if args.output_path is not None:
        save_day_assignment_evaluation_result(
            result_payload=result_payload,
            output_path=args.output_path,
        )

        print(
            "[Day Assignment Evaluation 성공]"
        )
        print(
            f"결과 저장 경로: "
            f"{args.output_path}"
        )
        return

    print(
        json.dumps(
            result_payload,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
