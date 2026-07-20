# 입력 순서 Baseline과 Held-Karp 정확 최적 경로를 비교하는 Evaluator
from time import perf_counter
from typing import List, Optional, Sequence, Tuple

from ai.route_planner.domain.schemas import (
    TravelMode,
    TravelTimeMatrix,
)
from ai.route_planner.domain.trip_schemas import (
    DayPlanDTO,
)
from ai.route_planner.evaluation.schemas import (
    RouteEvaluationResultDTO,
    RouteEvaluationStage,
    RouteStageEvaluationDTO,
)
from ai.route_planner.solvers.exact_route_solver import (
    ExactRouteNotFoundError,
    ExactRouteSolver,
)


# 정확 경로 최적화 품질과 실행 시간을 평가하는 클래스
class RouteEvaluator:
    def __init__(
        self,
        exact_route_solver: ExactRouteSolver | None = None,
    ):
        self.exact_route_solver = (
            exact_route_solver
            or ExactRouteSolver()
        )

    # 입력 순서와 Held-Karp 전역 최적 경로 비교
    def evaluate(
        self,
        scenario_id: str,
        day_plan: DayPlanDTO,
        travel_mode: TravelMode,
        travel_time_matrix: TravelTimeMatrix,
    ) -> RouteEvaluationResultDTO:
        start_place_id = (
            day_plan.start_place.place_id
        )
        end_place_id = (
            day_plan.end_place.place_id
        )
        poi_place_ids = [
            poi.place_id
            for poi in day_plan.assigned_pois
        ]

        baseline_place_ids = [
            start_place_id,
            *poi_place_ids,
            end_place_id,
        ]

        baseline = self._evaluate_existing_route(
            stage=RouteEvaluationStage.BASELINE,
            ordered_place_ids=baseline_place_ids,
            travel_time_matrix=travel_time_matrix,
            runtime_ms=0.0,
        )

        started_at = perf_counter()

        try:
            exact_result = (
                self.exact_route_solver.solve(
                    start_place_id=start_place_id,
                    poi_place_ids=poi_place_ids,
                    end_place_id=end_place_id,
                    travel_time_matrix=(
                        travel_time_matrix
                    ),
                )
            )
        except ExactRouteNotFoundError:
            runtime_ms = (
                perf_counter() - started_at
            ) * 1000

            exact_stage = RouteStageEvaluationDTO(
                stage=(
                    RouteEvaluationStage
                    .EXACT_DYNAMIC_PROGRAMMING
                ),
                ordered_place_ids=[],
                total_travel_minutes=None,
                runtime_ms=round(runtime_ms, 4),
                missing_segments=(
                    self._collect_missing_candidate_segments(
                        start_place_id=start_place_id,
                        poi_place_ids=poi_place_ids,
                        end_place_id=end_place_id,
                        travel_time_matrix=(
                            travel_time_matrix
                        ),
                    )
                ),
            )

            return RouteEvaluationResultDTO(
                scenario_id=scenario_id,
                travel_mode=travel_mode,
                baseline=baseline,
                exact_dynamic_programming=(
                    exact_stage
                ),
                improvement_minutes=None,
                improvement_ratio=None,
                evaluated_state_count=0,
                complete_route_found=False,
            )

        runtime_ms = (
            perf_counter() - started_at
        ) * 1000

        exact_stage = RouteStageEvaluationDTO(
            stage=(
                RouteEvaluationStage
                .EXACT_DYNAMIC_PROGRAMMING
            ),
            ordered_place_ids=list(
                exact_result.ordered_place_ids
            ),
            total_travel_minutes=(
                exact_result.total_travel_minutes
            ),
            runtime_ms=round(runtime_ms, 4),
            missing_segments=[],
        )

        (
            improvement_minutes,
            improvement_ratio,
        ) = self._calculate_improvement(
            baseline_total=(
                baseline.total_travel_minutes
            ),
            exact_total=(
                exact_result.total_travel_minutes
            ),
        )

        return RouteEvaluationResultDTO(
            scenario_id=scenario_id,
            travel_mode=travel_mode,
            baseline=baseline,
            exact_dynamic_programming=exact_stage,
            improvement_minutes=(
                improvement_minutes
            ),
            improvement_ratio=improvement_ratio,
            evaluated_state_count=(
                exact_result.evaluated_state_count
            ),
            complete_route_found=True,
        )

    # 이미 정해진 경로의 비용과 누락 구간 평가
    def _evaluate_existing_route(
        self,
        stage: RouteEvaluationStage,
        ordered_place_ids: Sequence[str],
        travel_time_matrix: TravelTimeMatrix,
        runtime_ms: float,
    ) -> RouteStageEvaluationDTO:
        total_minutes = 0
        missing_segments: List[str] = []

        for origin_place_id, destination_place_id in zip(
            ordered_place_ids,
            ordered_place_ids[1:],
        ):
            travel_minutes = (
                travel_time_matrix.get(
                    (
                        origin_place_id,
                        destination_place_id,
                    )
                )
            )

            if travel_minutes is None:
                missing_segments.append(
                    f"{origin_place_id} -> "
                    f"{destination_place_id}"
                )
                continue

            total_minutes += travel_minutes

        return RouteStageEvaluationDTO(
            stage=stage,
            ordered_place_ids=list(
                ordered_place_ids
            ),
            total_travel_minutes=(
                None
                if missing_segments
                else total_minutes
            ),
            runtime_ms=round(runtime_ms, 4),
            missing_segments=missing_segments,
        )

    # 정확 경로 생성 후보에 필요한 누락 간선 진단
    def _collect_missing_candidate_segments(
        self,
        start_place_id: str,
        poi_place_ids: Sequence[str],
        end_place_id: str,
        travel_time_matrix: TravelTimeMatrix,
    ) -> List[str]:
        missing_segments: List[str] = []

        # START에서는 각 POI 또는 END로 이동 가능
        start_destinations = [
            *poi_place_ids,
            end_place_id,
        ]

        for destination_place_id in start_destinations:
            self._append_missing_segment(
                origin_place_id=start_place_id,
                destination_place_id=(
                    destination_place_id
                ),
                travel_time_matrix=travel_time_matrix,
                missing_segments=missing_segments,
            )

        # POI에서는 다른 POI 또는 END로 이동 가능
        for origin_place_id in poi_place_ids:
            destinations = [
                poi_place_id
                for poi_place_id in poi_place_ids
                if poi_place_id
                != origin_place_id
            ]
            destinations.append(end_place_id)

            for destination_place_id in destinations:
                self._append_missing_segment(
                    origin_place_id=(
                        origin_place_id
                    ),
                    destination_place_id=(
                        destination_place_id
                    ),
                    travel_time_matrix=(
                        travel_time_matrix
                    ),
                    missing_segments=(
                        missing_segments
                    ),
                )

        return missing_segments

    # Matrix에 없는 후보 구간 추가
    def _append_missing_segment(
        self,
        origin_place_id: str,
        destination_place_id: str,
        travel_time_matrix: TravelTimeMatrix,
        missing_segments: List[str],
    ) -> None:
        if (
            origin_place_id,
            destination_place_id,
        ) in travel_time_matrix:
            return

        segment = (
            f"{origin_place_id} -> "
            f"{destination_place_id}"
        )

        if segment not in missing_segments:
            missing_segments.append(segment)

    # Baseline 대비 정확 경로 개선량과 개선율 계산
    def _calculate_improvement(
        self,
        baseline_total: Optional[int],
        exact_total: Optional[int],
    ) -> Tuple[Optional[int], Optional[float]]:
        if (
            baseline_total is None
            or exact_total is None
        ):
            return None, None

        improvement_minutes = (
            baseline_total - exact_total
        )

        if baseline_total == 0:
            if exact_total == 0:
                return improvement_minutes, 0.0

            return improvement_minutes, None

        return (
            improvement_minutes,
            round(
                improvement_minutes
                / baseline_total
                * 100,
                4,
            ),
        )
