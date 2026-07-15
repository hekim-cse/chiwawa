# 고정 JSON Scenario를 기반으로 Day Assignment 클러스터링 평가를 실행하는 Script
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from ai.route_planner.evaluation.clustering_evaluator import (
    ClusteringEvaluator,
)
from ai.route_planner.evaluation.schemas import (
    ClusteringEvaluationScenarioDTO,
)
from ai.route_planner.solvers.day_assignment_solver import (
    DayAssignmentSolver,
)


# JSON Scenario 파일 로드
def load_clustering_evaluation_scenario(
    fixture_path: Path,
) -> ClusteringEvaluationScenarioDTO:
    with fixture_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return ClusteringEvaluationScenarioDTO.model_validate(
        payload
    )


# Clustering Evaluation 실행
def run_clustering_evaluation(
    scenario: ClusteringEvaluationScenarioDTO,
) -> Dict[str, Any]:
    response = DayAssignmentSolver().assign_pois_to_days(
        scenario.request
    )

    result = ClusteringEvaluator().evaluate(
        scenario_id=scenario.scenario_id,
        request=scenario.request,
        response=response,
    )

    return result.model_dump(
        mode="json"
    )


# 평가 결과 JSON 파일 저장
def save_clustering_evaluation_result(
    result_payload: Dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result_payload,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


# CLI 인자 파싱
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Day Assignment 클러스터링 평가 실행"
        )
    )
    parser.add_argument(
        "--fixture-path",
        type=Path,
        required=True,
        help="평가 Scenario JSON 경로",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        required=False,
        help="평가 결과 JSON 저장 경로",
    )

    return parser.parse_args()


# CLI Entrypoint
def main() -> None:
    args = parse_args()

    scenario = load_clustering_evaluation_scenario(
        args.fixture_path
    )
    result_payload = run_clustering_evaluation(
        scenario
    )

    if args.output_path is not None:
        save_clustering_evaluation_result(
            result_payload=result_payload,
            output_path=args.output_path,
        )

        print("[Clustering Evaluation 성공]")
        print(
            f"결과 저장 경로: {args.output_path}"
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
