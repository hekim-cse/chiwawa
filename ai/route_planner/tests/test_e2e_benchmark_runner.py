# 고정 Matrix 기반 Route Planner E2E Benchmark 전체 실행 검증
from ai.route_planner.benchmark.e2e_benchmark_runner import (
    RoutePlannerE2EBenchmarkRunner,
)
from ai.route_planner.benchmark.schemas import (
    BenchmarkMatrixDTO,
    RoutePlannerE2EBenchmarkScenarioDTO,
)
from ai.route_planner.domain.schemas import (
    TravelMode,
)
from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)
from ai.route_planner.tests.test_route_option_solver import (
    make_request_payload,
)


# place_id 집합의 모든 방향 이동 구간을 고정 비용으로 생성
def make_complete_matrix(
    travel_mode: TravelMode,
    place_ids: list[str],
    travel_minutes: int,
) -> BenchmarkMatrixDTO:
    return BenchmarkMatrixDTO.model_validate(
        {
            "travel_mode": travel_mode,
            "location_place_ids": (
                place_ids
            ),
            "entries": [
                {
                    "origin_place_id": origin,
                    "destination_place_id": (
                        destination
                    ),
                    "travel_minutes": (
                        travel_minutes
                    ),
                }
                for origin in place_ids
                for destination in place_ids
                if origin != destination
            ],
        }
    )


def make_scenario(
    repeat_count: int = 3,
) -> RoutePlannerE2EBenchmarkScenarioDTO:
    request = (
        TripPlanningRequestDTO
        .model_validate(
            make_request_payload()
        )
    )

    day = request.days[0]

    place_ids = [
        day.start_place.place_id,
        *[
            poi.place_id
            for poi in request.pois
        ],
        day.end_place.place_id,
    ]

    matrices = [
        make_complete_matrix(
            travel_mode=travel_mode,
            place_ids=place_ids,
            travel_minutes=travel_minutes,
        )
        for travel_mode, travel_minutes
        in (
            (
                TravelMode.DRIVE,
                10,
            ),
            (
                TravelMode.WALK,
                20,
            ),
            (
                TravelMode.TRANSIT,
                15,
            ),
        )
    ]

    return (
        RoutePlannerE2EBenchmarkScenarioDTO(
            scenario_id=(
                "route-planner-e2e-001"
            ),
            repeat_count=repeat_count,
            request=request,
            matrices=matrices,
        )
    )


# TripPlannerService 전체 파이프라인 반복 실행 및 결과 집계
def test_runner_executes_full_pipeline():
    result = (
        RoutePlannerE2EBenchmarkRunner()
        .run(
            make_scenario(
                repeat_count=2
            )
        )
    )

    assert result.scenario_id == (
        "route-planner-e2e-001"
    )
    assert result.repeat_count == 2
    assert len(result.runs) == 2

    assert result.total_elapsed_ms >= 0
    assert result.average_runtime_ms >= 0
    assert result.min_runtime_ms >= 0
    assert result.max_runtime_ms >= 0

    run = result.runs[0]

    assert run.assigned_poi_count == len(
        make_scenario().request.pois
    )
    assert run.unassigned_poi_count == 0
    assert run.complete_assignment is True

    assert run.route_option_count == 3
    assert run.timeline_count == 3
    assert run.warning_count == 0

    # 1일차 배정 Matrix 1회와
    # DRIVE/WALK/TRANSIT 경로 Matrix 3회
    assert run.provider_request_count == 4

    assert (
        run.provider_request_count_by_mode[
            TravelMode.DRIVE
        ]
        == 2
    )
    assert (
        run.provider_request_count_by_mode[
            TravelMode.WALK
        ]
        == 1
    )
    assert (
        run.provider_request_count_by_mode[
            TravelMode.TRANSIT
        ]
        == 1
    )


# 동일 입력의 반복 실행 결과 결정성 확인
def test_runner_reports_deterministic_result():
    result = (
        RoutePlannerE2EBenchmarkRunner()
        .run(
            make_scenario(
                repeat_count=3
            )
        )
    )

    assert result.deterministic is True

    fingerprints = {
        run.result_fingerprint
        for run in result.runs
    }

    assert len(fingerprints) == 1


# 반복 실행 사이 Provider 계측값이 누적되지 않음
def test_runner_resets_provider_metrics_between_runs():
    result = (
        RoutePlannerE2EBenchmarkRunner()
        .run(
            make_scenario(
                repeat_count=2
            )
        )
    )

    assert [
        run.provider_request_count
        for run in result.runs
    ] == [
        4,
        4,
    ]
