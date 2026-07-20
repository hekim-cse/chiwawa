# 정확 일자 배정 평가 Fixture 로드와 실행 및 결과 저장을 검증하는 테스트
import json
from pathlib import Path

import pytest

from ai.route_planner.evaluation.schemas import (
    DayAssignmentEvaluationScenarioDTO,
)
from ai.route_planner.scripts.run_day_assignment_evaluation import (
    build_travel_time_matrices_by_day,
    load_day_assignment_evaluation_scenario,
    run_day_assignment_evaluation,
    save_day_assignment_evaluation_result,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "day_assignment_evaluation_scenario.json"
)


# Fixture를 정확 일자 배정 평가 Scenario로 검증
def test_load_day_assignment_evaluation_scenario():
    scenario = (
        load_day_assignment_evaluation_scenario(
            FIXTURE_PATH
        )
    )

    assert isinstance(
        scenario,
        DayAssignmentEvaluationScenarioDTO,
    )
    assert scenario.scenario_id == (
        "day-assignment-evaluation-001"
    )
    assert len(scenario.request.days) == 2
    assert len(scenario.request.pois) == 4


# 명시적 Matrix로 정확 일자 배정 평가 실행
def test_run_day_assignment_evaluation():
    scenario = (
        load_day_assignment_evaluation_scenario(
            FIXTURE_PATH
        )
    )

    result_payload = (
        run_day_assignment_evaluation(
            scenario
        )
    )

    assert result_payload["scenario_id"] == (
        "day-assignment-evaluation-001"
    )
    assert (
        result_payload["assigned_poi_count"]
        == 4
    )
    assert (
        result_payload["unassigned_poi_count"]
        == 0
    )
    assert (
        result_payload[
            "unassigned_must_visit_count"
        ]
        == 0
    )
    assert (
        result_payload[
            "preferred_day_violation_count"
        ]
        == 0
    )
    assert (
        result_payload["complete_assignment"]
        is True
    )
    assert (
        result_payload[
            "evaluated_state_count"
        ]
        > 0
    )
    assert len(result_payload["days"]) == 2


# 평가 결과가 JSON 파일로 저장되는지 검증
def test_save_day_assignment_evaluation_result(
    tmp_path,
):
    scenario = (
        load_day_assignment_evaluation_scenario(
            FIXTURE_PATH
        )
    )
    result_payload = (
        run_day_assignment_evaluation(
            scenario
        )
    )

    output_path = (
        tmp_path
        / "day_assignment_evaluation_result.json"
    )

    save_day_assignment_evaluation_result(
        result_payload=result_payload,
        output_path=output_path,
    )

    saved_payload = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert saved_payload == result_payload


# 동일한 날짜 Matrix가 중복되면 거부
def test_rejects_duplicate_day_matrix():
    scenario = (
        load_day_assignment_evaluation_scenario(
            FIXTURE_PATH
        )
    )

    invalid_scenario = scenario.model_copy(
        update={
            "travel_time_entries_by_day": [
                *scenario
                .travel_time_entries_by_day,
                scenario
                .travel_time_entries_by_day[0],
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="Duplicated day matrix",
    ):
        build_travel_time_matrices_by_day(
            invalid_scenario
        )
