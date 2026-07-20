# 명시적 날짜별 Matrix로 정확 일자 배정 결과와 제약 준수 여부를 평가하는 Evaluator
from __future__ import annotations

from time import perf_counter
from typing import Mapping

from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)
from ai.route_planner.evaluation.schemas import (
    DayAssignmentEvaluationDayDTO,
    DayAssignmentEvaluationResultDTO,
)
from ai.route_planner.solvers.exact_day_assignment_solver import (
    ExactDayAssignmentSolver,
    TravelTimeMatricesByDay,
)


# 정확 일자 배정 Solver의 결과를 평가 DTO로 변환
class DayAssignmentEvaluator:
    def __init__(
        self,
        exact_day_assignment_solver: (
            ExactDayAssignmentSolver | None
        ) = None,
    ) -> None:
        self._exact_day_assignment_solver = (
            exact_day_assignment_solver
            or ExactDayAssignmentSolver()
        )

    # 정확 일자 배정 실행시간과 배정 제약 준수 결과 평가
    def evaluate(
        self,
        scenario_id: str,
        request: TripPlanningRequestDTO,
        travel_time_matrices_by_day: (
            TravelTimeMatricesByDay
        ),
    ) -> DayAssignmentEvaluationResultDTO:
        started_at = perf_counter()

        exact_result = (
            self._exact_day_assignment_solver
            .solve(
                days=request.days,
                pois=request.pois,
                travel_time_matrices_by_day=(
                    travel_time_matrices_by_day
                ),
            )
        )

        runtime_ms = (
            perf_counter() - started_at
        ) * 1000

        poi_by_id = {
            poi.poi_id: poi
            for poi in request.pois
        }

        if len(poi_by_id) != len(
            request.pois
        ):
            raise ValueError(
                "poi_id는 중복될 수 없습니다."
            )

        assigned_day_by_poi_id = (
            self._build_assigned_day_by_poi_id(
                exact_result
                .assigned_poi_ids_by_day
            )
        )

        unknown_poi_ids = (
            set(assigned_day_by_poi_id)
            | set(
                exact_result
                .unassigned_poi_ids
            )
        ) - set(poi_by_id)

        if unknown_poi_ids:
            raise ValueError(
                "정확 일자 배정 결과에 "
                "알 수 없는 poi_id가 포함되었습니다: "
                + ", ".join(
                    sorted(unknown_poi_ids)
                )
            )

        assigned_poi_count = len(
            assigned_day_by_poi_id
        )
        unassigned_poi_count = len(
            exact_result.unassigned_poi_ids
        )

        unassigned_must_visit_count = sum(
            1
            for poi_id
            in exact_result.unassigned_poi_ids
            if poi_by_id[poi_id].must_visit
        )

        preferred_day_violation_count = (
            self._count_preferred_day_violations(
                poi_by_id=poi_by_id,
                assigned_day_by_poi_id=(
                    assigned_day_by_poi_id
                ),
            )
        )

        days = [
            DayAssignmentEvaluationDayDTO(
                day_index=day.day_index,
                assigned_poi_ids=list(
                    exact_result
                    .assigned_poi_ids_by_day
                    .get(day.day_index, ())
                ),
                assigned_poi_count=len(
                    exact_result
                    .assigned_poi_ids_by_day
                    .get(day.day_index, ())
                ),
            )
            for day in sorted(
                request.days,
                key=lambda item: item.day_index,
            )
        ]

        return (
            DayAssignmentEvaluationResultDTO(
                scenario_id=scenario_id,
                total_travel_minutes=(
                    exact_result
                    .total_travel_minutes
                ),
                assigned_poi_count=(
                    assigned_poi_count
                ),
                unassigned_poi_count=(
                    unassigned_poi_count
                ),
                unassigned_must_visit_count=(
                    unassigned_must_visit_count
                ),
                preferred_day_violation_count=(
                    preferred_day_violation_count
                ),
                complete_assignment=(
                    unassigned_poi_count == 0
                ),
                evaluated_state_count=(
                    exact_result
                    .evaluated_state_count
                ),
                runtime_ms=runtime_ms,
                unassigned_poi_ids=list(
                    exact_result
                    .unassigned_poi_ids
                ),
                days=days,
            )
        )

    # POI가 여러 날짜에 중복 배정되지 않았는지 검증하며 조회 Map 생성
    def _build_assigned_day_by_poi_id(
        self,
        assigned_poi_ids_by_day: Mapping[
            int,
            tuple[str, ...],
        ],
    ) -> dict[str, int]:
        assigned_day_by_poi_id = {}

        for (
            day_index,
            assigned_poi_ids,
        ) in assigned_poi_ids_by_day.items():
            for poi_id in assigned_poi_ids:
                if (
                    poi_id
                    in assigned_day_by_poi_id
                ):
                    raise ValueError(
                        "동일한 POI가 여러 날짜에 "
                        "중복 배정되었습니다: "
                        f"{poi_id}"
                    )

                assigned_day_by_poi_id[
                    poi_id
                ] = day_index

        return assigned_day_by_poi_id

    # preferred_day_index가 지정된 배정 POI의 날짜 위반 수 계산
    def _count_preferred_day_violations(
        self,
        poi_by_id,
        assigned_day_by_poi_id,
    ) -> int:
        return sum(
            1
            for poi_id, day_index
            in assigned_day_by_poi_id.items()
            if (
                poi_by_id[poi_id]
                .preferred_day_index
                is not None
                and (
                    poi_by_id[poi_id]
                    .preferred_day_index
                    != day_index
                )
            )
        )
