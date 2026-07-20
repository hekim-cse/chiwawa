# 날짜별 이동시간 Matrix를 기반으로 POI의 전역 최적 일자 배정을 계산하는 정확 Solver
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Mapping, Optional, Sequence, Tuple

from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    PoiDTO,
)
from ai.route_planner.solvers.exact_route_solver import (
    ExactRouteNotFoundError,
    ExactRouteSolver,
)


# 장소 간 이동시간 Matrix 타입
TravelTimeMatrix = Mapping[Tuple[str, str], int]


# 날짜별 이동시간 Matrix 타입
TravelTimeMatricesByDay = Mapping[
    int,
    TravelTimeMatrix,
]


# 정확 일자 배정에서 허용하는 POI 수를 초과한 경우 발생하는 예외
class ExactDayAssignmentLimitExceededError(ValueError):
    pass


# 유효한 일자 배정 결과를 생성할 수 없는 경우 발생하는 예외
class ExactDayAssignmentNotFoundError(ValueError):
    pass


# 정확 일자 배정 입력 또는 결과의 식별자 무결성이 올바르지 않은 경우 발생하는 예외
class ExactDayAssignmentValidationError(ValueError):
    pass


# 정확 일자 배정 계산 제한 설정
@dataclass(frozen=True)
class ExactDayAssignmentSolverConfig:
    max_poi_count: int = 12

    def __post_init__(self) -> None:
        if self.max_poi_count < 0:
            raise ValueError(
                "max_poi_count는 0 이상이어야 합니다."
            )


# 하나의 날짜에 배정할 수 있는 POI 부분집합과 정확 경로 비용
@dataclass(frozen=True)
class DaySubsetCandidate:
    day_index: int
    poi_mask: int
    poi_ids: Tuple[str, ...]
    travel_minutes: int


# DP 상태에 저장하는 날짜별 부분집합 선택 결과
@dataclass(frozen=True)
class DayAssignmentState:
    assigned_mask: int
    total_travel_minutes: int
    assigned_poi_ids_by_day: Tuple[
        Tuple[int, Tuple[str, ...]],
        ...,
    ]


# 정확 일자 배정 결과
@dataclass(frozen=True)
class ExactDayAssignmentResult:
    assigned_poi_ids_by_day: Mapping[
        int,
        Tuple[str, ...],
    ]
    unassigned_poi_ids: Tuple[str, ...]
    total_travel_minutes: int
    evaluated_state_count: int


# 날짜별 POI 부분집합을 전부 탐색해 사전식 목적함수의 전역 최적해를 계산하는 Solver
class ExactDayAssignmentSolver:
    def __init__(
        self,
        exact_route_solver: Optional[
            ExactRouteSolver
        ] = None,
        config: Optional[
            ExactDayAssignmentSolverConfig
        ] = None,
    ) -> None:
        self._exact_route_solver = (
            exact_route_solver
            or ExactRouteSolver()
        )
        self._config = (
            config
            or ExactDayAssignmentSolverConfig()
        )

    # 날짜, POI, 날짜별 Matrix를 받아 정확 일자 배정 결과 생성
    def solve(
        self,
        days: Sequence[DayConstraintDTO],
        pois: Sequence[PoiDTO],
        travel_time_matrices_by_day: (
            TravelTimeMatricesByDay
        ),
    ) -> ExactDayAssignmentResult:
        normalized_days = tuple(
            sorted(
                days,
                key=lambda day: day.day_index,
            )
        )
        normalized_pois = tuple(
            sorted(
                pois,
                key=lambda poi: poi.poi_id,
            )
        )

        self._validate_inputs(
            days=normalized_days,
            pois=normalized_pois,
            travel_time_matrices_by_day=(
                travel_time_matrices_by_day
            ),
        )

        if len(normalized_pois) > (
            self._config.max_poi_count
        ):
            raise ExactDayAssignmentLimitExceededError(
                "정확 일자 배정 POI 제한을 "
                "초과했습니다: "
                f"max={self._config.max_poi_count}, "
                f"requested={len(normalized_pois)}. "
                "휴리스틱 fallback은 사용하지 않습니다."
            )

        poi_index_by_id = {
            poi.poi_id: index
            for index, poi in enumerate(
                normalized_pois
            )
        }

        candidates_by_day = {
            day.day_index: (
                self._build_day_candidates(
                    day=day,
                    pois=normalized_pois,
                    poi_index_by_id=poi_index_by_id,
                    travel_time_matrix=(
                        travel_time_matrices_by_day[
                            day.day_index
                        ]
                    ),
                )
            )
            for day in normalized_days
        }

        final_states, evaluated_state_count = (
            self._run_partition_dynamic_programming(
                days=normalized_days,
                candidates_by_day=(
                    candidates_by_day
                ),
            )
        )

        if not final_states:
            raise ExactDayAssignmentNotFoundError(
                "유효한 정확 일자 배정 결과를 "
                "생성할 수 없습니다."
            )

        best_state = min(
            final_states.values(),
            key=lambda state: (
                self._build_final_score(
                    state=state,
                    pois=normalized_pois,
                )
            ),
        )

        unassigned_poi_ids = tuple(
            poi.poi_id
            for index, poi in enumerate(
                normalized_pois
            )
            if not (
                best_state.assigned_mask
                & (1 << index)
            )
        )

        return ExactDayAssignmentResult(
            assigned_poi_ids_by_day=(
                MappingProxyType(
                    dict(
                        best_state
                        .assigned_poi_ids_by_day
                    )
                )
            ),
            unassigned_poi_ids=(
                unassigned_poi_ids
            ),
            total_travel_minutes=(
                best_state
                .total_travel_minutes
            ),
            evaluated_state_count=(
                evaluated_state_count
            ),
        )

    # 날짜별 가능한 모든 POI 부분집합과 정확 경로 비용 생성
    def _build_day_candidates(
        self,
        day: DayConstraintDTO,
        pois: Tuple[PoiDTO, ...],
        poi_index_by_id: Mapping[str, int],
        travel_time_matrix: TravelTimeMatrix,
    ) -> Tuple[DaySubsetCandidate, ...]:
        candidates = []

        try:
            empty_route_result = (
                self._exact_route_solver.solve(
                    start_place_id=(
                        day.start_place.place_id
                    ),
                    poi_place_ids=(),
                    end_place_id=(
                        day.end_place.place_id
                    ),
                    travel_time_matrix=(
                        travel_time_matrix
                    ),
                )
            )
        except ExactRouteNotFoundError:
            empty_route_result = None

        if empty_route_result is not None:
            candidates.append(
                DaySubsetCandidate(
                    day_index=day.day_index,
                    poi_mask=0,
                    poi_ids=(),
                    travel_minutes=(
                        empty_route_result
                        .total_travel_minutes
                    ),
                )
            )

        subset_count = 1 << len(pois)

        for poi_mask in range(
            1,
            subset_count,
        ):
            subset_pois = tuple(
                poi
                for index, poi in enumerate(pois)
                if poi_mask & (1 << index)
            )

            if not self._respects_day_constraints(
                day=day,
                subset_pois=subset_pois,
            ):
                continue

            try:
                route_result = (
                    self._exact_route_solver.solve(
                        start_place_id=(
                            day.start_place.place_id
                        ),
                        poi_place_ids=tuple(
                            poi.place_id
                            for poi in subset_pois
                        ),
                        end_place_id=(
                            day.end_place.place_id
                        ),
                        travel_time_matrix=(
                            travel_time_matrix
                        ),
                    )
                )
            except ExactRouteNotFoundError:
                continue

            poi_ids = tuple(
                sorted(
                    (
                        poi.poi_id
                        for poi in subset_pois
                    )
                )
            )

            normalized_mask = 0

            for poi_id in poi_ids:
                normalized_mask |= (
                    1
                    << poi_index_by_id[poi_id]
                )

            candidates.append(
                DaySubsetCandidate(
                    day_index=day.day_index,
                    poi_mask=normalized_mask,
                    poi_ids=poi_ids,
                    travel_minutes=(
                        route_result
                        .total_travel_minutes
                    ),
                )
            )

        return tuple(
            sorted(
                candidates,
                key=lambda candidate: (
                    candidate.poi_mask,
                    candidate.travel_minutes,
                    candidate.poi_ids,
                ),
            )
        )

    # POI 부분집합이 날짜별 강제 제약을 만족하는지 확인
    def _respects_day_constraints(
        self,
        day: DayConstraintDTO,
        subset_pois: Tuple[PoiDTO, ...],
    ) -> bool:
        if (
            day.max_place_count is not None
            and len(subset_pois)
            > day.max_place_count
        ):
            return False

        return all(
            poi.preferred_day_index is None
            or poi.preferred_day_index
            == day.day_index
            for poi in subset_pois
        )

    # 날짜별 부분집합 후보를 결합하는 정확 부분집합 DP 수행
    def _run_partition_dynamic_programming(
        self,
        days: Tuple[DayConstraintDTO, ...],
        candidates_by_day: Mapping[
            int,
            Tuple[DaySubsetCandidate, ...],
        ],
    ) -> Tuple[
        Dict[int, DayAssignmentState],
        int,
    ]:
        states: Dict[int, DayAssignmentState] = {
            0: DayAssignmentState(
                assigned_mask=0,
                total_travel_minutes=0,
                assigned_poi_ids_by_day=(),
            )
        }
        evaluated_state_count = 0

        for day in days:
            next_states: Dict[
                int,
                DayAssignmentState,
            ] = {}

            for state in states.values():
                for candidate in (
                    candidates_by_day[
                        day.day_index
                    ]
                ):
                    if (
                        state.assigned_mask
                        & candidate.poi_mask
                    ):
                        continue

                    evaluated_state_count += 1

                    next_mask = (
                        state.assigned_mask
                        | candidate.poi_mask
                    )
                    next_state = (
                        DayAssignmentState(
                            assigned_mask=next_mask,
                            total_travel_minutes=(
                                state
                                .total_travel_minutes
                                + candidate
                                .travel_minutes
                            ),
                            assigned_poi_ids_by_day=(
                                (
                                    *state
                                    .assigned_poi_ids_by_day,
                                    (
                                        day.day_index,
                                        candidate.poi_ids,
                                    ),
                                )
                            ),
                        )
                    )

                    current_state = (
                        next_states.get(next_mask)
                    )

                    if (
                        current_state is None
                        or self._build_state_key(
                            next_state
                        )
                        < self._build_state_key(
                            current_state
                        )
                    ):
                        next_states[next_mask] = (
                            next_state
                        )

            states = next_states

        return states, evaluated_state_count

    # 동일 assigned_mask 상태에서 최소 이동시간과 결정론적 배정을 선택
    def _build_state_key(
        self,
        state: DayAssignmentState,
    ) -> tuple:
        return (
            state.total_travel_minutes,
            state.assigned_poi_ids_by_day,
        )

    # 모든 최종 상태를 비교하는 사전식 목적함수 생성
    def _build_final_score(
        self,
        state: DayAssignmentState,
        pois: Tuple[PoiDTO, ...],
    ) -> tuple:
        unassigned_pois = tuple(
            poi
            for index, poi in enumerate(pois)
            if not (
                state.assigned_mask
                & (1 << index)
            )
        )

        unassigned_must_visit_count = sum(
            1
            for poi in unassigned_pois
            if poi.must_visit
        )

        # priority 숫자가 작을수록 우선순위가 높으므로
        # 우선순위별 미배정 개수를 앞에서부터 최소화
        unassigned_priority_counts = tuple(
            sum(
                1
                for poi in unassigned_pois
                if poi.priority == priority
            )
            for priority in range(1, 6)
        )

        return (
            unassigned_must_visit_count,
            len(unassigned_pois),
            unassigned_priority_counts,
            state.total_travel_minutes,
            state.assigned_poi_ids_by_day,
        )

    # 입력 식별자, 날짜, Matrix 무결성 검증
    def _validate_inputs(
        self,
        days: Tuple[DayConstraintDTO, ...],
        pois: Tuple[PoiDTO, ...],
        travel_time_matrices_by_day: (
            TravelTimeMatricesByDay
        ),
    ) -> None:
        if not days:
            raise ExactDayAssignmentValidationError(
                "정확 일자 배정에는 최소 한 개의 "
                "날짜가 필요합니다."
            )

        day_indexes = tuple(
            day.day_index
            for day in days
        )

        if len(set(day_indexes)) != len(
            day_indexes
        ):
            raise ExactDayAssignmentValidationError(
                "day_index는 중복될 수 없습니다."
            )

        poi_ids = tuple(
            poi.poi_id
            for poi in pois
        )

        if len(set(poi_ids)) != len(poi_ids):
            raise ExactDayAssignmentValidationError(
                "poi_id는 중복될 수 없습니다."
            )

        poi_place_ids = tuple(
            poi.place_id
            for poi in pois
        )

        if len(set(poi_place_ids)) != len(
            poi_place_ids
        ):
            raise ExactDayAssignmentValidationError(
                "POI place_id는 중복될 수 없습니다."
            )

        valid_day_indexes = set(day_indexes)

        for poi in pois:
            if (
                poi.preferred_day_index
                is not None
                and poi.preferred_day_index
                not in valid_day_indexes
            ):
                raise (
                    ExactDayAssignmentValidationError(
                        "preferred_day_index에 "
                        "해당하는 날짜가 없습니다: "
                        f"poi_id={poi.poi_id}, "
                        "preferred_day_index="
                        f"{poi.preferred_day_index}"
                    )
                )

        missing_matrix_day_indexes = sorted(
            valid_day_indexes
            - set(
                travel_time_matrices_by_day
                .keys()
            )
        )

        if missing_matrix_day_indexes:
            raise ExactDayAssignmentValidationError(
                "날짜별 이동시간 Matrix가 "
                "누락되었습니다: "
                f"{missing_matrix_day_indexes}"
            )

        for day in days:
            place_ids = (
                day.start_place.place_id,
                *poi_place_ids,
                day.end_place.place_id,
            )

            if len(set(place_ids)) != len(
                place_ids
            ):
                raise ExactDayAssignmentValidationError(
                    "날짜의 START, POI, END "
                    "place_id는 모두 고유해야 합니다: "
                    f"day_index={day.day_index}"
                )
