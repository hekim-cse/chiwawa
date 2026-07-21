# Route Planner E2E Benchmark CLI의 실행과 결과 저장 검증
import json
from pathlib import Path

from ai.route_planner.scripts.run_e2e_benchmark import (
    load_scenario,
    main,
)


FIXTURE_PATH = Path(
    "ai/route_planner/tests/fixtures/"
    "e2e_benchmark_scenario.json"
)


# 고정 Fixture를 정상적으로 Scenario DTO로 로드
def test_load_scenario():
    scenario = load_scenario(
        FIXTURE_PATH
    )

    assert scenario.scenario_id == (
        "route-planner-e2e-001"
    )
    assert scenario.repeat_count == 3
    assert len(scenario.matrices) == 3


# CLI 실행 결과를 JSON 파일로 저장
def test_main_writes_benchmark_result(
    monkeypatch,
    tmp_path,
):
    output_path = (
        tmp_path
        / "e2e_benchmark_result.json"
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_e2e_benchmark",
            "--fixture-path",
            str(FIXTURE_PATH),
            "--output-path",
            str(output_path),
        ],
    )

    exit_code = main()

    assert exit_code == 0
    assert output_path.exists()

    payload = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert payload["scenario_id"] == (
        "route-planner-e2e-001"
    )
    assert payload["repeat_count"] == 3
    assert payload["deterministic"] is True
    assert len(payload["runs"]) == 3

    assert all(
        run["complete_assignment"]
        for run in payload["runs"]
    )


# 존재하지 않는 Fixture 경로는 실패 코드 반환
def test_main_returns_failure_for_missing_fixture(
    monkeypatch,
):
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_e2e_benchmark",
            "--fixture-path",
            "missing.json",
        ],
    )

    assert main() == 1
