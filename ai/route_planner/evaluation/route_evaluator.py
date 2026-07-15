# RouteOptionSolver의 단계별 경로 품질과 실행 시간을 평가하는 모듈
from time import perf_counter
from typing import Callable, List, Optional, Set, Tuple

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
from ai.route_planner.solvers.route_option_solver import (
    RouteNode,
    RouteOptionSolver,
)


# RouteOptionSolver의 각 최적화 단계를 실행하고 결과를 비교하는 평가기
class RouteEvaluator:
    def __init__(
        self,
        solver: RouteOptionSolver | None = None,
    ):
        self.solver = solver or RouteOptionSolver()

    # 입력 순서부터 최종 Local Search까지 단계별 평가 결과 생성 (평가 전체 시작점)
    def evaluate(
        self,
        scenario_id: str,
        day_plan: DayPlanDTO,
        travel_mode: TravelMode,
        travel_time_matrix: TravelTimeMatrix,
    ) -> RouteEvaluationResultDTO:
        start_node = self.solver._build_start_node(
            day_plan
        )
        end_node = self.solver._build_end_node(
            day_plan
        )
        poi_nodes = [
            self.solver._build_poi_node(poi)
            for poi in day_plan.assigned_pois
        ]

        expected_poi_place_ids = {
            node.place_id
            for node in poi_nodes
        }

        # Baseline은 사용자가 전달한 POI 순서를 그대로 사용
        baseline_route = [
            start_node,
            *poi_nodes,
            end_node,
        ]

        baseline_stage = self._evaluate_existing_route(
            stage=RouteEvaluationStage.BASELINE,
            route_nodes=baseline_route,
            travel_time_matrix=travel_time_matrix,
            previous_total_minutes=None,
            baseline_total_minutes=None,
            runtime_ms=0.0,
        )

        # Cheapest Insertion 후보 탐색 중 발생한 누락은 별도로 사용하지 않고,
        # 완성된 경로의 누락 구간만 Stage 결과에 기록
        cheapest_search_missing_segments: Set[str] = set()

        cheapest_started_at = perf_counter()
        (
            cheapest_route,
            uninserted_nodes,
        ) = (
            self.solver
            ._build_initial_route_by_cheapest_insertion(
                start_node=start_node,
                end_node=end_node,
                poi_nodes=poi_nodes,
                travel_time_matrix=travel_time_matrix,
                missing_segments=(
                    cheapest_search_missing_segments
                ),
            )
        )
        cheapest_runtime_ms = (
            perf_counter() - cheapest_started_at
        ) * 1000

        # Stage별 경로 불변조건 검증
        self._validate_route_invariants(
            route_nodes=cheapest_route,
            start_node=start_node,
            end_node=end_node,
            expected_poi_place_ids=(
                expected_poi_place_ids
            ),
        )

        cheapest_stage = self._evaluate_existing_route(
            stage=(
                RouteEvaluationStage
                .CHEAPEST_INSERTION
            ),
            route_nodes=cheapest_route,
            travel_time_matrix=travel_time_matrix,
            previous_total_minutes=(
                baseline_stage.total_travel_minutes
            ),
            baseline_total_minutes=(
                baseline_stage.total_travel_minutes
            ),
            runtime_ms=cheapest_runtime_ms,
        )

        # Cheapest Insertion 결과에 Relocate를 한 번 적용
        relocate_route, relocate_runtime_ms = (
            self._measure_route_operation(
                operation=lambda: (
                    self.solver
                    ._improve_route_by_relocate(
                        route_nodes=cheapest_route,
                        travel_time_matrix=(
                            travel_time_matrix
                        ),
                        missing_segments=set(),
                    )
                )
            )
        )

        self._validate_route_invariants(
            route_nodes=relocate_route,
            start_node=start_node,
            end_node=end_node,
            expected_poi_place_ids=(
                expected_poi_place_ids
            ),
        )

        relocate_stage = self._evaluate_existing_route(
            stage=RouteEvaluationStage.RELOCATE,
            route_nodes=relocate_route,
            travel_time_matrix=travel_time_matrix,
            previous_total_minutes=(
                cheapest_stage.total_travel_minutes
            ),
            baseline_total_minutes=(
                baseline_stage.total_travel_minutes
            ),
            runtime_ms=relocate_runtime_ms,
        )

        # Relocate 결과에 2-opt를 한 번 적용
        two_opt_route, two_opt_runtime_ms = (
            self._measure_route_operation(
                operation=lambda: (
                    self.solver
                    ._improve_route_by_two_opt(
                        route_nodes=relocate_route,
                        travel_time_matrix=(
                            travel_time_matrix
                        ),
                        missing_segments=set(),
                    )
                )
            )
        )

        self._validate_route_invariants(
            route_nodes=two_opt_route,
            start_node=start_node,
            end_node=end_node,
            expected_poi_place_ids=(
                expected_poi_place_ids
            ),
        )

        two_opt_stage = self._evaluate_existing_route(
            stage=RouteEvaluationStage.TWO_OPT,
            route_nodes=two_opt_route,
            travel_time_matrix=travel_time_matrix,
            previous_total_minutes=(
                relocate_stage.total_travel_minutes
            ),
            baseline_total_minutes=(
                baseline_stage.total_travel_minutes
            ),
            runtime_ms=two_opt_runtime_ms,
        )

        # 실제 운영 Solver와 동일하게 Cheapest Insertion 결과에서
        # Relocate와 2-opt를 수렴할 때까지 반복
        (
            final_route,
            final_runtime_ms,
        ) = self._measure_route_operation(
            operation=lambda: (
                self.solver
                ._improve_route_by_local_search(
                    route_nodes=cheapest_route,
                    travel_time_matrix=(
                        travel_time_matrix
                    ),
                    missing_segments=set(),
                )
            )
        )

        self._validate_route_invariants(
            route_nodes=final_route,
            start_node=start_node,
            end_node=end_node,
            expected_poi_place_ids=(
                expected_poi_place_ids
            ),
        )

        final_stage = self._evaluate_existing_route(
            stage=(
                RouteEvaluationStage
                .FINAL_LOCAL_SEARCH
            ),
            route_nodes=final_route,
            travel_time_matrix=travel_time_matrix,
            previous_total_minutes=(
                cheapest_stage.total_travel_minutes
            ),
            baseline_total_minutes=(
                baseline_stage.total_travel_minutes
            ),
            runtime_ms=final_runtime_ms,
        )

        return RouteEvaluationResultDTO(
            scenario_id=scenario_id,
            travel_mode=travel_mode,
            baseline=baseline_stage,
            cheapest_insertion=cheapest_stage,
            relocate=relocate_stage,
            two_opt=two_opt_stage,
            final_local_search=final_stage,
            uninserted_place_ids=[
                node.place_id
                for node in uninserted_nodes
            ],
        )

    # 이미 생성된 경로의 비용과 개선율을 평가
    def _evaluate_existing_route(
        self,
        stage: RouteEvaluationStage,
        route_nodes: List[RouteNode],
        travel_time_matrix: TravelTimeMatrix,
        previous_total_minutes: Optional[int],
        baseline_total_minutes: Optional[int],
        runtime_ms: float,
    ) -> RouteStageEvaluationDTO:
        missing_segments: Set[str] = set()

        # 총 이동시간 계산 시 누락 구간이 있으면 None 반환
        total_minutes = (
            self.solver
            ._calculate_route_total_minutes(
                route_nodes=route_nodes,
                travel_time_matrix=travel_time_matrix,
                missing_segments=missing_segments,
            )
        )

        # 이전 단계 대비 개선량과 개선율 계산
        (
            previous_improvement_minutes,
            previous_improvement_ratio,
        ) = self._calculate_improvement(
            reference_total_minutes=(
                previous_total_minutes
            ),
            current_total_minutes=total_minutes,
        )

        # Baseline 대비 개선량과 개선율 계산
        (
            baseline_improvement_minutes,
            baseline_improvement_ratio,
        ) = self._calculate_improvement(
            reference_total_minutes=(
                baseline_total_minutes
            ),
            current_total_minutes=total_minutes,
        )

        return RouteStageEvaluationDTO(
            stage=stage,
            ordered_place_ids=[
                node.place_id
                for node in route_nodes
            ],
            total_travel_minutes=total_minutes,
            improvement_minutes_from_previous=(
                previous_improvement_minutes
            ),
            improvement_ratio_from_previous=(
                previous_improvement_ratio
            ),
            improvement_minutes_from_baseline=(
                baseline_improvement_minutes
            ),
            improvement_ratio_from_baseline=(
                baseline_improvement_ratio
            ),
            runtime_ms=round(runtime_ms, 4),
            missing_segments=sorted(
                missing_segments
            ),
        )

    # 하나의 경로 최적화 단계 실행 시간을 측정
    def _measure_route_operation(
        self,
        operation: Callable[[], List[RouteNode]],
    ) -> Tuple[List[RouteNode], float]:
        started_at = perf_counter()
        route_nodes = operation()
        runtime_ms = (
            perf_counter() - started_at
        ) * 1000

        return route_nodes, runtime_ms

    # 기준 경로 대비 이동시간 절감량과 개선율 계산
    def _calculate_improvement(
        self,
        reference_total_minutes: Optional[int],
        current_total_minutes: Optional[int],
    ) -> Tuple[Optional[int], Optional[float]]:
        if (
            reference_total_minutes is None
            or current_total_minutes is None
        ):
            return None, None

        improvement_minutes = (
            reference_total_minutes
            - current_total_minutes
        )

        if reference_total_minutes == 0:
            if current_total_minutes == 0:
                return improvement_minutes, 0.0

            return improvement_minutes, None

        improvement_ratio = (
            improvement_minutes
            / reference_total_minutes
            * 100
        )

        return (
            improvement_minutes,
            round(improvement_ratio, 4),
        )

    # 평가 과정에서 START, END, POI 순서의 기본 불변조건 검증
    def _validate_route_invariants(
        self,
        route_nodes: List[RouteNode],
        start_node: RouteNode,
        end_node: RouteNode,
        expected_poi_place_ids: Set[str],
    ) -> None:
        if not route_nodes:
            raise ValueError(
                "Evaluated route must not be empty."
            )

        if route_nodes[0] != start_node:
            raise ValueError(
                "START node must remain first."
            )

        if route_nodes[-1] != end_node:
            raise ValueError(
                "END node must remain last."
            )

        route_poi_place_ids = [
            node.place_id
            for node in route_nodes[1:-1]
        ]

        if (
            len(route_poi_place_ids)
            != len(set(route_poi_place_ids))
        ):
            raise ValueError(
                "Evaluated route contains duplicated POIs."
            )

        if not set(route_poi_place_ids).issubset(
            expected_poi_place_ids
        ):
            raise ValueError(
                "Evaluated route contains unknown POIs."
            )
