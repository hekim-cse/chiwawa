# 고정 출발지와 도착지 사이의 정확한 최소 이동 경로를 계산하는 Solver
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ai.route_planner.domain.schemas import TravelTimeMatrix


# 정확 경로 최적화 입력 제한 초과 예외
class ExactRouteLimitExceededError(ValueError):
    pass


# 모든 POI를 방문하는 완전 경로 부재 예외
class ExactRouteNotFoundError(ValueError):
    pass


# 정확 경로 최적화 설정
@dataclass(frozen=True)
class ExactRouteSolverConfig:
    # 지수 복잡도를 명시적으로 제한
    max_poi_count: int = 12


# 정확 경로 최적화 결과
@dataclass(frozen=True)
class ExactRouteResult:
    ordered_place_ids: Tuple[str, ...]
    total_travel_minutes: int
    evaluated_state_count: int


# Held-Karp 부분집합 동적 계획법 기반 정확 경로 Solver
class ExactRouteSolver:
    def __init__(
        self,
        config: Optional[ExactRouteSolverConfig] = None,
    ):
        self.config = config or ExactRouteSolverConfig()

    # start → 모든 POI → end 형태의 전역 최소 경로 계산
    def solve(
        self,
        start_place_id: str,
        poi_place_ids: Sequence[str],
        end_place_id: str,
        travel_time_matrix: TravelTimeMatrix,
    ) -> ExactRouteResult:
        self._validate_inputs(
            start_place_id=start_place_id,
            poi_place_ids=poi_place_ids,
            end_place_id=end_place_id,
        )

        poi_ids = tuple(poi_place_ids)

        if not poi_ids:
            travel_minutes = travel_time_matrix.get(
                (start_place_id, end_place_id)
            )

            if travel_minutes is None:
                raise ExactRouteNotFoundError(
                    "출발지에서 도착지까지의 이동 구간이 없습니다: "
                    f"{start_place_id} -> {end_place_id}"
                )

            return ExactRouteResult(
                ordered_place_ids=(
                    start_place_id,
                    end_place_id,
                ),
                total_travel_minutes=travel_minutes,
                evaluated_state_count=1,
            )

        # key: (방문한 POI 비트마스크, 마지막 POI 인덱스)
        # value: (누적 이동시간, 직전 POI 인덱스)
        states: Dict[
            Tuple[int, int],
            Tuple[int, Optional[int]],
        ] = {}

        # 출발지에서 POI 하나를 방문한 초기 상태 생성
        for poi_index, poi_place_id in enumerate(poi_ids):
            travel_minutes = travel_time_matrix.get(
                (start_place_id, poi_place_id)
            )

            if travel_minutes is None:
                continue

            mask = 1 << poi_index
            states[(mask, poi_index)] = (
                travel_minutes,
                None,
            )

        full_mask = (1 << len(poi_ids)) - 1

        # 방문 부분집합 크기를 확장하며 모든 정확 상태 계산
        for mask in range(1, full_mask + 1):
            for last_index in range(len(poi_ids)):
                state = states.get((mask, last_index))

                if state is None:
                    continue

                current_minutes, _ = state
                origin_place_id = poi_ids[last_index]

                for next_index, destination_place_id in enumerate(
                    poi_ids
                ):
                    next_bit = 1 << next_index

                    if mask & next_bit:
                        continue

                    travel_minutes = travel_time_matrix.get(
                        (
                            origin_place_id,
                            destination_place_id,
                        )
                    )

                    if travel_minutes is None:
                        continue

                    next_mask = mask | next_bit
                    candidate_minutes = (
                        current_minutes + travel_minutes
                    )
                    next_key = (next_mask, next_index)
                    existing_state = states.get(next_key)

                    if (
                        existing_state is None
                        or candidate_minutes
                        < existing_state[0]
                    ):
                        states[next_key] = (
                            candidate_minutes,
                            last_index,
                        )

        # 모든 POI 방문 후 도착지까지 연결되는 최솟값 선택
        best_last_index: Optional[int] = None
        best_total_minutes: Optional[int] = None

        for last_index, last_place_id in enumerate(poi_ids):
            state = states.get(
                (full_mask, last_index)
            )

            if state is None:
                continue

            end_travel_minutes = travel_time_matrix.get(
                (last_place_id, end_place_id)
            )

            if end_travel_minutes is None:
                continue

            candidate_total = (
                state[0] + end_travel_minutes
            )

            if (
                best_total_minutes is None
                or candidate_total < best_total_minutes
            ):
                best_total_minutes = candidate_total
                best_last_index = last_index

        if (
            best_last_index is None
            or best_total_minutes is None
        ):
            raise ExactRouteNotFoundError(
                "모든 POI를 방문하는 완전 경로가 없습니다. "
                f"start={start_place_id}, "
                f"pois={list(poi_ids)}, "
                f"end={end_place_id}"
            )

        ordered_poi_ids = self._restore_order(
            states=states,
            full_mask=full_mask,
            last_index=best_last_index,
            poi_ids=poi_ids,
        )

        return ExactRouteResult(
            ordered_place_ids=(
                start_place_id,
                *ordered_poi_ids,
                end_place_id,
            ),
            total_travel_minutes=best_total_minutes,
            evaluated_state_count=len(states),
        )

    # DP 역추적으로 POI 방문 순서 복원
    def _restore_order(
        self,
        states: Dict[
            Tuple[int, int],
            Tuple[int, Optional[int]],
        ],
        full_mask: int,
        last_index: int,
        poi_ids: Tuple[str, ...],
    ) -> List[str]:
        reversed_order: List[str] = []
        mask = full_mask
        current_index: Optional[int] = last_index

        while current_index is not None:
            reversed_order.append(
                poi_ids[current_index]
            )

            _, previous_index = states[
                (mask, current_index)
            ]

            mask ^= 1 << current_index
            current_index = previous_index

        reversed_order.reverse()
        return reversed_order

    # 입력 무결성과 정확 계산 제한 검증
    def _validate_inputs(
        self,
        start_place_id: str,
        poi_place_ids: Sequence[str],
        end_place_id: str,
    ) -> None:
        if len(poi_place_ids) > self.config.max_poi_count:
            raise ExactRouteLimitExceededError(
                "정확 경로 최적화 POI 제한을 초과했습니다. "
                f"max_poi_count={self.config.max_poi_count}, "
                f"requested_poi_count={len(poi_place_ids)}. "
                "휴리스틱 fallback은 사용하지 않습니다."
            )

        all_place_ids = [
            start_place_id,
            *poi_place_ids,
            end_place_id,
        ]

        duplicate_place_ids = sorted(
            {
                place_id
                for place_id in all_place_ids
                if all_place_ids.count(place_id) > 1
            }
        )

        if duplicate_place_ids:
            raise ValueError(
                "경로의 place_id는 중복될 수 없습니다: "
                + ", ".join(duplicate_place_ids)
            )
