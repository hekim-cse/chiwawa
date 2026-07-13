# 여행 일정 생성 전체 UseCase를 조합하는 Application Service
from typing import Dict, List, Protocol

from ai.route_planner.domain.schemas import (
    Location,
    TravelMode,
    TravelTimeMatrixResult,
)
from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    DayPlanDTO,
    TripPlanningRequestDTO,
    TripPlanningResponseDTO,
)
from ai.route_planner.solvers.day_assignment_solver import (
    DayAssignmentSolver,
)
from ai.route_planner.solvers.route_options_by_mode_solver import (
    RouteOptionsByModeSolver,
)
from ai.route_planner.solvers.timeline_options_builder import (
    TimelineOptionsBuilder,
)


# 이동 방식별 이동 시간 행렬을 제공하는 Provider 인터페이스
# Service가 GoogleRoutesProvider 구체 구현에 직접 의존하지 않도록 분리
class TravelTimeMatrixProvider(Protocol):
    def build_travel_time_matrix_result(
        self,
        locations: List[Location],
        travel_mode: TravelMode,
    ) -> TravelTimeMatrixResult:
        ...


# 여행 요청 전체를 처리하는 Application Service
class TripPlannerService:
    def __init__(
        self,
        routes_provider: TravelTimeMatrixProvider,  # 장소 간 이동 시간 행렬을 생성하는 Provider / Provider 인터페이스를 주입받아 GoogleRoutesProvider 구체 구현에 직접 의존하지 않음
        day_assignment_solver: DayAssignmentSolver | None = None,   # POI를 day별로 배정하는 Solver
        route_options_solver: RouteOptionsByModeSolver | None = None,   # 이동 방식별 방문 순서를 생성하는 Solver 
        timeline_options_builder: TimelineOptionsBuilder | None = None, # 이동 방식별 시간표를 생성하는 Builder 
    ):
        self.routes_provider = routes_provider
        self.day_assignment_solver = (
            day_assignment_solver
            or DayAssignmentSolver()
        )
        self.route_options_solver = (
            route_options_solver
            or RouteOptionsByModeSolver()
        )
        self.timeline_options_builder = (
            timeline_options_builder
            or TimelineOptionsBuilder()
        )

    # 여행 요청을 받아 day 배정, 경로 옵션, Timeline이 포함된 최종 응답을 생성
    def plan_trip(
        self,
        request: TripPlanningRequestDTO,
    ) -> TripPlanningResponseDTO:
        trip_response = (
            self.day_assignment_solver.assign_pois_to_days(
                request
            )
        )

        day_constraints_by_index = (
            self._build_day_constraints_by_index(
                request
            )
        )

        updated_day_plans: List[DayPlanDTO] = []

        for day_plan in trip_response.day_plans:
            day_constraint = day_constraints_by_index.get(
                day_plan.day_index
            )

            if day_constraint is None:
                raise ValueError(
                    "DayConstraintDTO not found for day_index: "
                    f"{day_plan.day_index}"
                )

            matrix_results_by_mode = (
                self._build_matrix_results_by_mode(
                    day_plan
                )
            )

            day_plan_with_route_options = (
                self.route_options_solver.assign_route_options(
                    day_plan=day_plan,
                    matrix_results_by_mode=(
                        matrix_results_by_mode
                    ),
                )
            )

            day_plan_with_timelines = (
                self.timeline_options_builder.assign_timelines(
                    day_constraint=day_constraint,
                    day_plan=day_plan_with_route_options,
                )
            )

            updated_day_plans.append(
                day_plan_with_timelines
            )

        # 원본 응답 DTO를 직접 수정하지 않고 갱신된 새 DTO 반환
        return trip_response.model_copy(
            update={
                "day_plans": updated_day_plans,
            }
        )

    # day_index를 key로 하는 DayConstraintDTO 조회 맵 생성
    def _build_day_constraints_by_index(
        self,
        request: TripPlanningRequestDTO,
    ) -> Dict[int, DayConstraintDTO]:
        return {
            day_constraint.day_index: day_constraint
            for day_constraint in request.days
        }

    # 하나의 day에 대해 설정된 이동 방식별 Matrix 결과 생성
    def _build_matrix_results_by_mode(
        self,
        day_plan: DayPlanDTO,
    ) -> Dict[TravelMode, TravelTimeMatrixResult]:
        locations = self._build_locations_from_day_plan(
            day_plan
        )

        return {
            travel_mode: (
                self.routes_provider
                .build_travel_time_matrix_result(
                    locations=locations,
                    travel_mode=travel_mode,
                )
            )
            for travel_mode in (
                TravelMode.DRIVE,
                TravelMode.WALK,
                TravelMode.TRANSIT,
            )
        }

    # DayPlanDTO의 장소를 Provider 요청용 Location으로 변환
    # Location.name에는 Matrix key로 사용할 place_id 저장
    def _build_locations_from_day_plan(
        self,
        day_plan: DayPlanDTO,
    ) -> List[Location]:
        return [
            Location(
                name=day_plan.start_place.place_id,
                lat=day_plan.start_place.lat,
                lng=day_plan.start_place.lng,
            ),
            *[
                Location(
                    name=poi.place_id,
                    lat=poi.lat,
                    lng=poi.lng,
                )
                for poi in day_plan.assigned_pois
            ],
            Location(
                name=day_plan.end_place.place_id,
                lat=day_plan.end_place.lat,
                lng=day_plan.end_place.lng,
            ),
        ]
