# 정확 일자 배정 Matrix 선조회부터 경로 옵션과 Timeline 생성까지 조합하는 Application Service
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
from ai.route_planner.solvers.exact_day_assignment_solver import (
    TravelTimeMatricesByDay,
)
from ai.route_planner.solvers.route_options_by_mode_solver import (
    RouteOptionsByModeSolver,
)
from ai.route_planner.solvers.timeline_options_builder import (
    TimelineOptionsBuilder,
)


# 이동시간 Matrix를 제공하는 Provider 인터페이스
class TravelTimeMatrixProvider(Protocol):
    def build_travel_time_matrix_result(
        self,
        locations: List[Location],
        travel_mode: TravelMode,
        departure_time: datetime | None = None,
    ) -> TravelTimeMatrixResult:
        ...


# 여행 계획 Service의 명시적 실행 설정
@dataclass(frozen=True)
class TripPlannerServiceConfig:
    day_assignment_travel_mode: TravelMode


# 정확 일자 배정과 경로 및 Timeline 생성을 조합하는 Application Service
class TripPlannerService:
    def __init__(
        self,
        routes_provider: TravelTimeMatrixProvider,
        config: TripPlannerServiceConfig,
        day_assignment_solver: DayAssignmentSolver | None = None,
        route_options_solver: RouteOptionsByModeSolver | None = None,
        timeline_options_builder: TimelineOptionsBuilder | None = None,
    ) -> None:
        self.routes_provider = routes_provider
        self.config = config
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

    # Matrix 선조회, 정확 일자 배정, 경로 옵션, Timeline 순서로 최종 응답 생성
    def plan_trip(
        self,
        request: TripPlanningRequestDTO,
    ) -> TripPlanningResponseDTO:
        assignment_matrices_by_day = (
            self._build_assignment_matrices_by_day(
                request=request,
            )
        )

        trip_response = (
            self.day_assignment_solver
            .assign_pois_to_days(
                request=request,
                travel_time_matrices_by_day=(
                    assignment_matrices_by_day
                ),
            )
        )

        day_constraints_by_index = (
            self._build_day_constraints_by_index(
                request
            )
        )

        updated_day_plans: List[DayPlanDTO] = []

        for day_plan in trip_response.day_plans:
            day_constraint = (
                day_constraints_by_index.get(
                    day_plan.day_index
                )
            )

            if day_constraint is None:
                raise ValueError(
                    "DayConstraintDTO not found for "
                    "day_index: "
                    f"{day_plan.day_index}"
                )

            matrix_results_by_mode = (
                self._build_route_matrix_results_by_mode(
                    day_plan=day_plan,
                    day_constraint=day_constraint,
                    timezone_name=request.timezone,
                )
            )

            day_plan_with_route_options = (
                self.route_options_solver
                .assign_route_options(
                    day_plan=day_plan,
                    matrix_results_by_mode=(
                        matrix_results_by_mode
                    ),
                )
            )

            day_plan_with_timelines = (
                self.timeline_options_builder
                .assign_timelines(
                    day_constraint=day_constraint,
                    day_plan=(
                        day_plan_with_route_options
                    ),
                )
            )

            updated_day_plans.append(
                day_plan_with_timelines
            )

        return trip_response.model_copy(
            update={
                "day_plans": updated_day_plans,
            }
        )

    # 각 날짜의 START, 전체 후보 POI, END를 사용해 정확 배정 Matrix 선조회
    def _build_assignment_matrices_by_day(
        self,
        request: TripPlanningRequestDTO,
    ) -> TravelTimeMatricesByDay:
        matrices_by_day = {}

        for day in sorted(
            request.days,
            key=lambda item: item.day_index,
        ):
            locations = (
                self._build_assignment_locations(
                    day=day,
                    request=request,
                )
            )

            matrix_result = (
                self.routes_provider
                .build_travel_time_matrix_result(
                    locations=locations,
                    travel_mode=(
                        self.config
                        .day_assignment_travel_mode
                    ),
                    departure_time=(
                        self._build_departure_time(
                            day=day,
                            timezone_name=(
                                request.timezone
                            ),
                        )
                    ),
                )
            )

            # Provider 누락 구간에는 가짜 비용을 보충하지 않고
            # 정상 계산된 Matrix 구간만 정확 Solver에 전달
            matrices_by_day[day.day_index] = (
                matrix_result.matrix
            )

        return matrices_by_day

    # 하나의 날짜와 전체 후보 POI를 일자 배정 Provider 요청 Location으로 변환
    def _build_assignment_locations(
        self,
        day: DayConstraintDTO,
        request: TripPlanningRequestDTO,
    ) -> List[Location]:
        locations = [
            Location(
                name=day.start_place.place_id,
                lat=day.start_place.lat,
                lng=day.start_place.lng,
            ),
            *[
                Location(
                    name=poi.place_id,
                    lat=poi.lat,
                    lng=poi.lng,
                )
                for poi in request.pois
            ],
            Location(
                name=day.end_place.place_id,
                lat=day.end_place.lat,
                lng=day.end_place.lng,
            ),
        ]

        self._validate_unique_location_names(
            locations=locations,
            context=(
                "정확 일자 배정 Matrix "
                f"day_index={day.day_index}"
            ),
        )

        return locations

    # 하나의 배정 완료 날짜에 대해 모든 경로 이동 방식 Matrix 생성
    def _build_route_matrix_results_by_mode(
        self,
        day_plan: DayPlanDTO,
        day_constraint: DayConstraintDTO,
        timezone_name: str,
    ) -> Dict[
        TravelMode,
        TravelTimeMatrixResult,
    ]:
        locations = (
            self._build_locations_from_day_plan(
                day_plan=day_plan,
            )
        )

        departure_time = (
            self._build_departure_time(
                day=day_constraint,
                timezone_name=timezone_name,
            )
        )

        return {
            travel_mode: (
                self.routes_provider
                .build_travel_time_matrix_result(
                    locations=locations,
                    travel_mode=travel_mode,
                    departure_time=departure_time,
                )
            )
            for travel_mode in (
                TravelMode.DRIVE,
                TravelMode.WALK,
                TravelMode.TRANSIT,
            )
        }

    # 배정 완료 DayPlan의 장소를 경로 Provider 요청 Location으로 변환
    def _build_locations_from_day_plan(
        self,
        day_plan: DayPlanDTO,
    ) -> List[Location]:
        locations = [
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

        self._validate_unique_location_names(
            locations=locations,
            context=(
                "경로 옵션 Matrix "
                f"day_index={day_plan.day_index}"
            ),
        )

        return locations

    # 여행 날짜와 시작 시각을 timezone-aware datetime으로 변환
    @staticmethod
    def _build_departure_time(
        day: DayConstraintDTO,
        timezone_name: str,
    ) -> datetime:
        try:
            timezone = ZoneInfo(
                timezone_name
            )
        except ZoneInfoNotFoundError as error:
            raise ValueError(
                "지원하지 않는 timezone입니다: "
                f"{timezone_name}"
            ) from error

        try:
            local_departure_time = (
                datetime.fromisoformat(
                    f"{day.date}T"
                    f"{day.start_time}"
                )
            )
        except ValueError as error:
            raise ValueError(
                "여행 날짜 또는 시작 시각 형식이 "
                "올바르지 않습니다: "
                f"date={day.date}, "
                f"start_time={day.start_time}"
            ) from error

        if (
            local_departure_time.tzinfo
            is not None
        ):
            raise ValueError(
                "start_time에는 timezone offset을 "
                "포함할 수 없습니다."
            )

        return local_departure_time.replace(
            tzinfo=timezone
        )

    # Matrix key 충돌을 방지하기 위해 Location.name 중복 검증
    def _validate_unique_location_names(
        self,
        locations: List[Location],
        context: str,
    ) -> None:
        location_names = [
            location.name
            for location in locations
        ]

        if len(
            location_names
        ) != len(
            set(location_names)
        ):
            raise ValueError(
                f"{context}의 place_id는 "
                "모두 고유해야 합니다."
            )

    # day_index를 key로 하는 날짜 제약 조회 Map 생성
    def _build_day_constraints_by_index(
        self,
        request: TripPlanningRequestDTO,
    ) -> Dict[int, DayConstraintDTO]:
        day_constraints_by_index = {
            day.day_index: day
            for day in request.days
        }

        if len(
            day_constraints_by_index
        ) != len(
            request.days
        ):
            raise ValueError(
                "day_index는 중복될 수 없습니다."
            )

        return day_constraints_by_index
