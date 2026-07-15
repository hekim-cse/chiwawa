# Clustering Evaluation 실행 Script 단위 테스트
import json
from pathlib import Path

from ai.route_planner.evaluation.schemas import (
    ClusteringEvaluationScenarioDTO,
)
from ai.route_planner.scripts.run_clustering_evaluation import (
    load_clustering_evaluation_scenario,
    run_clustering_evaluation,
    save_clustering_evaluation_result,
)


FIXTURE_PATH = Path(
    "ai/route_planner/tests/fixtures/"
    "clustering_evaluation_scenario.json"
)


# 고정 Fixture를 Scenario DTO로 읽는지 검증
def test_load_clustering_evaluation_scenario():
    scenario = load_clustering_evaluation_scenario(
        FIXTURE_PATH
    )

    assert isinstance(
        scenario,
        ClusteringEvaluationScenarioDTO,
    )
    assert (
        scenario.scenario_id
        == "clustering-evaluation-001"
    )
    assert len(scenario.request.days) == 2
    assert len(scenario.request.pois) == 4


# 고정 Fixture 평가 결과 검증
def test_run_clustering_evaluation():
    scenario = load_clustering_evaluation_scenario(
        FIXTURE_PATH
    )

    result_payload = run_clustering_evaluation(
        scenario
    )

    assert (
        result_payload["scenario_id"]
        == "clustering-evaluation-001"
    )
    assert result_payload["assigned_poi_count"] == 4
    assert result_payload["unassigned_poi_count"] == 0
    assert result_payload["assignment_rate"] == 100.0
    assert (
        result_payload[
            "preferred_day_compliance_rate"
        ]
        == 100.0
    )
    assert (
        result_payload[
            "must_visit_assignment_rate"
        ]
        == 100.0
    )
    assert result_payload["silhouette_score"] > 0.9
    assert len(result_payload["day_clusters"]) == 2


# 평가 결과가 JSON 파일로 저장되는지 검증
def test_save_clustering_evaluation_result(
    tmp_path,
):
    scenario = load_clustering_evaluation_scenario(
        FIXTURE_PATH
    )
    result_payload = run_clustering_evaluation(
        scenario
    )

    output_path = (
        tmp_path
        / "clustering_evaluation_result.json"
    )

    save_clustering_evaluation_result(
        result_payload=result_payload,
        output_path=output_path,
    )

    saved_payload = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert saved_payload == result_payload
