# 고정 Matrix 기반으로 Route Planner 전체 파이프라인을 반복 실행하는 E2E Benchmark Runner
from __future__ import annotations

import hashlib
import json
from time import perf_counter

from ai.route_planner.benchmark.fixture_routes_provider import (
    FixtureTravelTimeMatrixProvider,
)
from ai.route_planner.benchmark.instrumented_routes_provider import (
    InstrumentedTravelTimeMatrixProvider,
)
from ai.route_planner.benchmark.schemas import (
    RoutePlannerE2EBenchmarkResultDTO,
    RoutePlannerE2EBenchmarkRunDTO,
    RoutePlannerE2EBenchmarkScenarioDTO,
)
from ai.route_planner.domain.schemas import (
    TravelMode,
)
from ai.route_planner.domain.trip_schemas import (
    TripPlanningResponseDTO,
)
from ai.route_planner.services.trip_planner_service import (
    TripPlannerService,
    TripPlannerServiceConfig,
)


# Scenario의 고정 Matrix로 전체 Trip Planner 실행 결과를 측정
class RoutePlannerE2EBenchmarkRunner:
    def run(
        self,
        scenario: RoutePlannerE2EBenchmarkScenarioDTO,
    ) -> RoutePlannerE2EBenchmarkResultDTO:
        fixture_provider = (
            FixtureTravelTimeMatrixProvider(
                matrices=scenario.matrices,
            )
        )

        instrumented_provider = (
            InstrumentedTravelTimeMatrixProvider(
                delegate=fixture_provider,
            )
        )

        service = TripPlannerService(
            routes_provider=(
                instrumented_provider
            ),
            config=TripPlannerServiceConfig(
                day_assignment_travel_mode=(
                    TravelMode.DRIVE
                ),
            ),
        )

        runs: list[
            RoutePlannerE2EBenchmarkRunDTO
        ] = []

        benchmark_started_at = perf_counter()

        for _ in range(
            scenario.repeat_count
        ):
            instrumented_provider.reset()

            run_started_at = perf_counter()

            response = service.plan_trip(
                scenario.request
            )

            runtime_ms = (
                perf_counter() - run_started_at
            ) * 1000

            provider_metrics = (
                instrumented_provider.snapshot()
            )

            runs.append(
                self._build_run_result(
                    request_poi_count=len(
                        scenario.request.pois
                    ),
                    response=response,
                    runtime_ms=runtime_ms,
                    provider_metrics=(
                        provider_metrics
                    ),
                )
            )

        total_elapsed_ms = (
            perf_counter()
            - benchmark_started_at
        ) * 1000

        runtime_values = [
            run.runtime_ms
            for run in runs
        ]

        fingerprints = {
            run.result_fingerprint
            for run in runs
        }

        return (
            RoutePlannerE2EBenchmarkResultDTO(
                scenario_id=(
                    scenario.scenario_id
                ),
                repeat_count=len(runs),
                total_elapsed_ms=round(
                    total_elapsed_ms,
                    4,
                ),
                average_runtime_ms=round(
                    sum(runtime_values)
                    / len(runtime_values),
                    4,
                ),
                min_runtime_ms=round(
                    min(runtime_values),
                    4,
                ),
                max_runtime_ms=round(
                    max(runtime_values),
                    4,
                ),
                deterministic=(
                    len(fingerprints) == 1
                ),
                runs=runs,
            )
        )

    @staticmethod
    def _build_run_result(
        request_poi_count: int,
        response: TripPlanningResponseDTO,
        runtime_ms: float,
        provider_metrics,
    ) -> RoutePlannerE2EBenchmarkRunDTO:
        unassigned_poi_count = len(
            response.unassigned_pois
        )

        assigned_poi_count = (
            request_poi_count
            - unassigned_poi_count
        )

        route_option_count = sum(
            len(day_plan.route_options)
            for day_plan
            in response.day_plans
        )

        timeline_count = sum(
            1
            for day_plan
            in response.day_plans
            for route_option
            in day_plan.route_options
            if route_option.timeline is not None
        )

        return RoutePlannerE2EBenchmarkRunDTO(
            runtime_ms=round(
                runtime_ms,
                4,
            ),
            provider_request_count=(
                provider_metrics.request_count
            ),
            provider_request_count_by_mode=(
                provider_metrics
                .request_count_by_mode
            ),
            provider_expected_element_count=(
                provider_metrics
                .expected_element_count
            ),
            provider_returned_element_count=(
                provider_metrics
                .returned_element_count
            ),
            provider_missing_element_count=(
                provider_metrics
                .missing_element_count
            ),
            provider_runtime_ms=(
                provider_metrics
                .total_runtime_ms
            ),
            assigned_poi_count=(
                assigned_poi_count
            ),
            unassigned_poi_count=(
                unassigned_poi_count
            ),
            warning_count=len(
                response.warnings
            ),
            route_option_count=(
                route_option_count
            ),
            timeline_count=timeline_count,
            complete_assignment=(
                unassigned_poi_count == 0
            ),
            result_fingerprint=(
                RoutePlannerE2EBenchmarkRunner
                ._build_result_fingerprint(
                    response
                )
            ),
        )

    @staticmethod
    def _build_result_fingerprint(
        response: TripPlanningResponseDTO,
    ) -> str:
        serialized_response = json.dumps(
            response.model_dump(
                mode="json"
            ),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            serialized_response.encode(
                "utf-8"
            )
        ).hexdigest()
