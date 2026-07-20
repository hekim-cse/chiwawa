# 고정 Matrix로 정확 일자 배정 DayPlan을 생성하고 정확 경로 최적화 평가를 실행하는 CLI 스크립트
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from ai.route_planner.domain.schemas import (
    TravelTimeMatrix,
)
from ai.route_planner.domain.trip_schemas import (
    DayPlanDTO,
)
from ai.route_planner.evaluation.route_evaluator import (
    RouteEvaluator,
)
from ai.route_planner.evaluation.schemas import (
    RouteEvaluationResultDTO,
    RouteEvaluationScenarioDTO,
)
from ai.route_planner.solvers.day_assignment_solver import (
    DayAssignmentSolver,
)


# 평가 Scenario JSON 파일을 읽고 DTO로 검증
def load_route_evaluation_scenario(
    fixture_path: Path,
) -> RouteEvaluationScenarioDTO:
    with fixture_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return (
        RouteEvaluationScenarioDTO
        .model_validate(payload)
    )


# JSON 구간 목록을 tuple key Matrix로 변환
def build_travel_time_matrix(
    scenario: RouteEvaluationScenarioDTO,
) -> TravelTimeMatrix:
    matrix: TravelTimeMatrix = {}

    for entry in scenario.travel_time_entries:
        key = (
            entry.origin_place_id,
            entry.destination_place_id,
        )

        if key in matrix:
            raise ValueError(
                "Duplicated travel time entry: "
                f"{entry.origin_place_id} -> "
                f"{entry.destination_place_id}"
            )

        matrix[key] = entry.travel_minutes

    return matrix


# Route Evaluation Scenario가 단일 날짜 Matrix 계약을 만족하는지 검증
def validate_single_day_scenario(
    scenario: RouteEvaluationScenarioDTO,
) -> None:
    if len(scenario.request.days) != 1:
        raise ValueError(
            "Route Evaluation Scenario는 "
            "정확 일자 배정에 필요한 Matrix를 "
            "하나만 제공하므로 request.days가 "
            "정확히 한 개여야 합니다."
        )

    request_day = scenario.request.days[0]

    if request_day.day_index != scenario.day_index:
        raise ValueError(
            "Route Evaluation day_index와 "
            "request의 유일한 day_index가 "
            "일치해야 합니다: "
            f"scenario={scenario.day_index}, "
            f"request={request_day.day_index}"
        )


# Day Assignment 결과에서 평가 대상으로 지정된 날짜 조회
def find_day_plan(
    day_plans: list[DayPlanDTO],
    day_index: int,
) -> DayPlanDTO:
    for day_plan in day_plans:
        if day_plan.day_index == day_index:
            return day_plan

    raise ValueError(
        "DayPlanDTO not found for evaluation "
        f"day_index: {day_index}"
    )


# Scenario Matrix로 정확 일자 배정 후 경로 평가 실행
def run_route_evaluation(
    scenario: RouteEvaluationScenarioDTO,
    evaluator: RouteEvaluator | None = None,
) -> RouteEvaluationResultDTO:
    validate_single_day_scenario(
        scenario
    )

    travel_time_matrix = (
        build_travel_time_matrix(
            scenario
        )
    )

    trip_response = (
        DayAssignmentSolver()
        .assign_pois_to_days(
            request=scenario.request,
            travel_time_matrices_by_day={
                scenario.day_index: (
                    travel_time_matrix
                ),
            },
        )
    )

    day_plan = find_day_plan(
        day_plans=trip_response.day_plans,
        day_index=scenario.day_index,
    )

    route_evaluator = (
        evaluator
        or RouteEvaluator()
    )

    return route_evaluator.evaluate(
        scenario_id=scenario.scenario_id,
        day_plan=day_plan,
        travel_mode=scenario.travel_mode,
        travel_time_matrix=travel_time_matrix,
    )


# 평가 결과를 JSON 파일로 저장
def save_route_evaluation_result(
    result: RouteEvaluationResultDTO,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            result.model_dump(
                mode="json"
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# CLI 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "고정 Matrix Scenario를 기반으로 "
            "정확 일자 배정 DayPlan을 생성하고 "
            "입력 순서와 정확 경로 결과를 비교합니다."
        )
    )

    parser.add_argument(
        "--fixture-path",
        required=True,
        help=(
            "Route Evaluation Scenario "
            "JSON 경로입니다."
        ),
    )

    parser.add_argument(
        "--output-path",
        help=(
            "평가 결과를 저장할 JSON 경로입니다. "
            "생략하면 표준 출력으로 출력합니다."
        ),
    )

    args = parser.parse_args()

    try:
        scenario = (
            load_route_evaluation_scenario(
                Path(args.fixture_path)
            )
        )
        result = run_route_evaluation(
            scenario
        )
    except (
        ValidationError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        print("[Route Evaluation 실패]")
        print(error)
        raise SystemExit(1)

    if args.output_path:
        output_path = Path(
            args.output_path
        )

        save_route_evaluation_result(
            result=result,
            output_path=output_path,
        )

        print("[Route Evaluation 성공]")
        print(
            f"결과 저장 경로: {output_path}"
        )
        return

    print("[Route Evaluation 성공]")
    print(
        json.dumps(
            result.model_dump(
                mode="json"
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
