# Route Planner E2E Benchmark 입력 및 결과 스키마 검증
import pytest
from pydantic import ValidationError

from ai.route_planner.benchmark.schemas import (
    BenchmarkMatrixDTO,
    RoutePlannerE2EBenchmarkScenarioDTO,
)
from ai.route_planner.domain.schemas import (
    TravelMode,
)
from ai.route_planner.tests.test_route_option_solver import (
    make_request_payload,
)


def make_matrix_payload() -> dict:
    place_ids = [
        "start",
        "poi_1",
        "end",
    ]

    return {
        "travel_mode": "DRIVE",
        "location_place_ids": place_ids,
        "entries": [
            {
                "origin_place_id": origin,
                "destination_place_id": (
                    destination
                ),
                "travel_minutes": 10,
            }
            for origin in place_ids
            for destination in place_ids
            if origin != destination
        ],
    }



# 정상 Scenario 입력 검증
def test_scenario_accepts_valid_input():
    scenario = (
        RoutePlannerE2EBenchmarkScenarioDTO
        .model_validate(
            {
                "scenario_id": "benchmark-001",
                "repeat_count": 3,
                "request": make_request_payload(),
                "matrices": [
                    make_matrix_payload(),
                ],
            }
        )
    )

    assert scenario.scenario_id == (
        "benchmark-001"
    )
    assert scenario.repeat_count == 3
    assert (
        scenario.matrices[0].travel_mode
        == TravelMode.DRIVE
    )


# 동일 Location 집합과 이동 방식 Matrix 중복 거부
def test_scenario_rejects_duplicated_matrix_key():
    matrix = make_matrix_payload()

    with pytest.raises(
        ValidationError,
        match="중복",
    ):
        (
            RoutePlannerE2EBenchmarkScenarioDTO
            .model_validate(
                {
                    "scenario_id": (
                        "benchmark-001"
                    ),
                    "request": (
                        make_request_payload()
                    ),
                    "matrices": [
                        matrix,
                        matrix,
                    ],
                }
            )
        )


# Matrix Location 중복 거부
def test_matrix_rejects_duplicated_locations():
    payload = make_matrix_payload()
    payload["location_place_ids"] = [
        "start",
        "poi_1",
        "poi_1",
        "end",
    ]

    with pytest.raises(
        ValidationError,
        match="중복",
    ):
        BenchmarkMatrixDTO.model_validate(
            payload
        )


# Matrix에 없는 장소를 사용하는 구간 거부
def test_matrix_rejects_unknown_entry_place():
    payload = make_matrix_payload()
    payload["entries"].append(
        {
            "origin_place_id": "unknown",
            "destination_place_id": "end",
            "travel_minutes": 10,
        }
    )

    with pytest.raises(
        ValidationError,
        match="포함",
    ):
        BenchmarkMatrixDTO.model_validate(
            payload
        )


# 동일 이동 구간 중복 거부
def test_matrix_rejects_duplicated_entry():
    payload = make_matrix_payload()
    payload["entries"].append(
        dict(payload["entries"][0])
    )

    with pytest.raises(
        ValidationError,
        match="중복 이동 구간",
    ):
        BenchmarkMatrixDTO.model_validate(
            payload
        )


# 모든 방향 이동 구간이 정의되지 않은 Matrix 거부
def test_matrix_rejects_missing_entry():
    payload = make_matrix_payload()
    payload["entries"].pop()

    with pytest.raises(
        ValidationError,
        match="필수 이동 구간이 누락",
    ):
        BenchmarkMatrixDTO.model_validate(
            payload
        )
