# 이동 방식별 TravelTimeMatrixResult를 기반으로 여러 Route Option을 생성하는 Solver
from dataclasses import dataclass
from typing import Mapping, Tuple

from ai.route_planner.domain.schemas import (
    TravelMode,
    TravelTimeMatrixResult,
)
from ai.route_planner.domain.trip_schemas import DayPlanDTO, RouteOptionDTO
from ai.route_planner.solvers.exact_route_solver import (
    ExactRouteNotFoundError,
)
from ai.route_planner.solvers.route_option_solver import RouteOptionSolver


# 이동 방식별 Route Option 생성 설정
@dataclass(frozen=True)
class RouteOptionsByModeSolverConfig:
    # Route Option을 생성할 이동 방식과 결과 출력 순서
    travel_modes: Tuple[TravelMode, ...] = (
        TravelMode.DRIVE,
        TravelMode.WALK,
        TravelMode.TRANSIT,
    )


# 하나의 DayPlanDTO에 이동 방식별 Route Option을 생성해 주입하는 Solver
class RouteOptionsByModeSolver:
    def __init__(
        self,
        route_option_solver: RouteOptionSolver | None = None,   # 이동 방식 하나의 경로를 최적화하는 Solver
        config: RouteOptionsByModeSolverConfig | None = None,   # 생성할 이동 방식과 순서를 정의하는 설정
    ):
        self.route_option_solver = route_option_solver or RouteOptionSolver()
        self.config = config or RouteOptionsByModeSolverConfig()

    # DayPlanDTO에 이동 방식별 RouteOptionDTO를 생성해 주입하는 함수
    def assign_route_options(
        self,
        day_plan: DayPlanDTO,   # Day Assignment 결과
        matrix_results_by_mode: Mapping[    # 이동 방식별 이동 시간 행렬 생성 결과
            TravelMode,
            TravelTimeMatrixResult,
        ],
    ) -> DayPlanDTO:    # 반환: route_options가 주입된 새로운 DayPlanDTO
        self._validate_matrix_results(matrix_results_by_mode)

        route_options = [
            self._build_route_option(
                day_plan=day_plan,
                travel_mode=travel_mode,
                matrix_result=matrix_results_by_mode[travel_mode],
            )
            for travel_mode in self.config.travel_modes
        ]

        # 기존 DayPlanDTO를 직접 변경하지 않고 route_options가 적용된 새 모델을 반환
        # 부수 효과를 피하고, Pydantic 모델의 불변성을 유지하기 위함
        return day_plan.model_copy(
            update={
                "route_options": route_options,
            }
        )

    # 이동 방식 하나에 대한 RouteOptionDTO를 생성하는 함수
    def _build_route_option(
        self,
        day_plan: DayPlanDTO,
        travel_mode: TravelMode,
        matrix_result: TravelTimeMatrixResult,
    ) -> RouteOptionDTO:
        # Provider가 계산하지 못한 실제 이동 구간 목록 생성
        provider_missing_segments = [
            (
                f"{element.origin_name} -> "
                f"{element.destination_name}"
            )
            for element in matrix_result.missing_elements
            if element.origin_index != element.destination_index
        ]

        try:
            route_option = (
                self.route_option_solver
                .solve_route_option(
                    day_plan=day_plan,
                    travel_mode=travel_mode,
                    travel_time_matrix=(
                        matrix_result.matrix
                    ),
                )
            )
        except ExactRouteNotFoundError:
            # Provider 누락 구간이 없는 완전한 Matrix에서 발생한
            # 도메인 오류는 숨기지 않고 그대로 전달
            if not provider_missing_segments:
                raise

            return RouteOptionDTO(
                day_index=day_plan.day_index,
                travel_mode=travel_mode,
                total_travel_minutes=0,
                ordered_stops=[],
                route_legs=[],
                missing_segments=sorted(
                    set(
                        provider_missing_segments
                    )
                ),
                warnings=[
                    (
                        f"{travel_mode.value} 이동 방식은 "
                        "모든 장소를 방문하는 완전한 "
                        "경로를 생성할 수 없습니다."
                    ),
                    (
                        "Google Routes Provider에서 "
                        "계산하지 못한 이동 구간이 "
                        "있습니다: "
                        + ", ".join(
                            provider_missing_segments
                        )
                    ),
                ],
            )

        if not provider_missing_segments:
            return route_option

        warnings = list(route_option.warnings)
        warnings.append(
            "Google Routes Provider에서 계산하지 못한 이동 구간이 있습니다: "
            + ", ".join(provider_missing_segments)
        )

        # Provider 누락 구간과 Solver 탐색 중 발견된 누락 구간을 합쳐 중복 없이 반환
        missing_segments = sorted(
            {
                *route_option.missing_segments,
                *provider_missing_segments,
            }
        )

        return route_option.model_copy(
            update={
                "missing_segments": missing_segments,
                "warnings": warnings,
            }
        )

    # 설정된 모든 이동 방식의 matrix 결과가 전달되었는지 검증하는 함수
    def _validate_matrix_results(
        self,
        matrix_results_by_mode: Mapping[
            TravelMode,
            TravelTimeMatrixResult,
        ],
    ) -> None:
        missing_modes = [
            travel_mode.value
            for travel_mode in self.config.travel_modes
            if travel_mode not in matrix_results_by_mode
        ]

        if missing_modes:
            raise ValueError(
                "Missing travel time matrix results for modes: "
                + ", ".join(missing_modes)
            )
