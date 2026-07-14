# Route Evaluation Script의 입력 변환과 결과 저장 테스트
import json
from pathlib import Path

import pytest

from ai.route_planner.evaluation.schemas import (
    RouteEvaluationScenarioDTO,
)
from ai.route_planner.scripts.run_route_evaluation import (
    build_travel_time_matrix,
    load_route_evaluation_scenario,
    run_route_evaluation,
    save_route_evaluation_result,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "route_evaluation_scenario.json"
)


# Fixture를 검증하고 단계별 평가 결과를 생성하는지 확인
def test_run_route_evaluation_returns_result():
    scenario = load_route_evaluation_scenario(
        FIXTURE_PATH
    )

    result = run_route_evaluation(
        scenario
    )

    assert result.scenario_id == (
        "route-evaluation-001"
    )
    assert (
        result.baseline.total_travel_minutes
        == 140
    )
    assert (
        result.cheapest_insertion
        .total_travel_minutes
        == 40
    )
    assert (
        result.final_local_search
        .total_travel_minutes
        <= result.cheapest_insertion
        .total_travel_minutes
    )


# 평가 결과가 JSON 파일로 저장되는지 확인
def test_save_route_evaluation_result(
    tmp_path: Path,
):
    scenario = load_route_evaluation_scenario(
        FIXTURE_PATH
    )
    result = run_route_evaluation(
        scenario
    )

    output_path = (
        tmp_path
        / "route_evaluation_result.json"
    )

    save_route_evaluation_result(
        result=result,
        output_path=output_path,
    )

    payload = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert payload["scenario_id"] == (
        "route-evaluation-001"
    )
    assert (
        payload["baseline"]
        ["total_travel_minutes"]
        == 140
    )
    assert (
        payload["cheapest_insertion"]
        ["total_travel_minutes"]
        == 40
    )


# 같은 이동 구간이 중복 정의되면 명시적으로 실패하는지 확인
def test_build_travel_time_matrix_rejects_duplicates():
    scenario = (
        RouteEvaluationScenarioDTO
        .model_validate_json(
            FIXTURE_PATH.read_text(
                encoding="utf-8"
            )
        )
    )

    duplicated_entry = (
        scenario.travel_time_entries[0]
        .model_copy()
    )

    duplicated_scenario = scenario.model_copy(
        update={
            "travel_time_entries": [
                *scenario.travel_time_entries,
                duplicated_entry,
            ]
        }
    )

    with pytest.raises(
        ValueError,
        match="Duplicated travel time entry",
    ):
        build_travel_time_matrix(
            duplicated_scenario
        )
