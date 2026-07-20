# 정확 경로 최적화 결과를 RouteOptionDTO로 변환하는 도메인 어댑터
from dataclasses import dataclass
from typing import Dict, List, Mapping, Tuple

from ai.route_planner.domain.schemas import (
    TravelMode,
    TravelTimeMatrix,
)
from ai.route_planner.domain.trip_schemas import (
    DayPlanDTO,
    PoiDTO,
    RouteLegDTO,
    RouteOptionDTO,
    RouteStopDTO,
    RouteStopType,
)
from ai.route_planner.solvers.exact_route_solver import (
    ExactRouteResult,
    ExactRouteSolver,
)


# 정확 경로 계산과 DTO 변환에 필요한 불변 컨텍스트
@dataclass(frozen=True)
class RouteOptionContext:
    start_place_id: str
    end_place_id: str
    poi_place_ids: Tuple[str, ...]
    stops_by_place_id: Mapping[str, RouteStopDTO]


# 정확 경로 Solver와 여행 도메인 DTO 사이를 연결하는 어댑터
class RouteOptionSolver:
    def __init__(
        self,
        exact_route_solver: ExactRouteSolver | None = None,
    ):
        self.exact_route_solver = (
            exact_route_solver
            or ExactRouteSolver()
        )

    # DayPlanDTO와 이동시간 Matrix로 정확한 RouteOptionDTO 생성
    def solve_route_option(
        self,
        day_plan: DayPlanDTO,
        travel_mode: TravelMode,
        travel_time_matrix: TravelTimeMatrix,
    ) -> RouteOptionDTO:
        context = self._build_context(day_plan)

        exact_result = self.exact_route_solver.solve(
            start_place_id=context.start_place_id,
            poi_place_ids=context.poi_place_ids,
            end_place_id=context.end_place_id,
            travel_time_matrix=travel_time_matrix,
        )

        self._validate_exact_result(
            context=context,
            exact_result=exact_result,
        )

        ordered_stops = self._build_ordered_stops(
            ordered_place_ids=(
                exact_result.ordered_place_ids
            ),
            stops_by_place_id=(
                context.stops_by_place_id
            ),
        )

        route_legs = self._build_route_legs(
            ordered_place_ids=(
                exact_result.ordered_place_ids
            ),
            travel_time_matrix=travel_time_matrix,
        )

        self._validate_route_legs(
            exact_result=exact_result,
            route_legs=route_legs,
        )

        return RouteOptionDTO(
            day_index=day_plan.day_index,
            travel_mode=travel_mode,
            total_travel_minutes=(
                exact_result.total_travel_minutes
            ),
            ordered_stops=ordered_stops,
            route_legs=route_legs,
            missing_segments=[],
            warnings=[],
        )

    # DayPlanDTO를 정확 경로 계산용 불변 컨텍스트로 변환
    def _build_context(
        self,
        day_plan: DayPlanDTO,
    ) -> RouteOptionContext:
        start_stop = RouteStopDTO(
            stop_type=RouteStopType.START,
            place_id=day_plan.start_place.place_id,
            name=day_plan.start_place.name,
            lat=day_plan.start_place.lat,
            lng=day_plan.start_place.lng,
        )

        end_stop = RouteStopDTO(
            stop_type=RouteStopType.END,
            place_id=day_plan.end_place.place_id,
            name=day_plan.end_place.name,
            lat=day_plan.end_place.lat,
            lng=day_plan.end_place.lng,
        )

        poi_stops = [
            self._build_poi_stop(poi)
            for poi in day_plan.assigned_pois
        ]

        all_stops = [
            start_stop,
            *poi_stops,
            end_stop,
        ]

        place_ids = [
            stop.place_id
            for stop in all_stops
        ]

        duplicate_place_ids = sorted(
            {
                place_id
                for place_id in place_ids
                if place_ids.count(place_id) > 1
            }
        )

        if duplicate_place_ids:
            raise ValueError(
                "DayPlanDTO의 place_id는 중복될 수 없습니다: "
                + ", ".join(duplicate_place_ids)
            )

        return RouteOptionContext(
            start_place_id=start_stop.place_id,
            end_place_id=end_stop.place_id,
            poi_place_ids=tuple(
                stop.place_id
                for stop in poi_stops
            ),
            stops_by_place_id={
                stop.place_id: stop
                for stop in all_stops
            },
        )

    # POI를 RouteStopDTO로 변환
    def _build_poi_stop(
        self,
        poi: PoiDTO,
    ) -> RouteStopDTO:
        return RouteStopDTO(
            stop_type=RouteStopType.POI,
            place_id=poi.place_id,
            name=poi.name,
            lat=poi.lat,
            lng=poi.lng,
        )

    # 정확 경로 결과의 장소 집합과 순서 불변조건 검증
    def _validate_exact_result(
        self,
        context: RouteOptionContext,
        exact_result: ExactRouteResult,
    ) -> None:
        ordered_place_ids = (
            exact_result.ordered_place_ids
        )

        if len(ordered_place_ids) < 2:
            raise ValueError(
                "정확 경로 결과에는 START와 END가 필요합니다."
            )

        if (
            ordered_place_ids[0]
            != context.start_place_id
        ):
            raise ValueError(
                "정확 경로 결과의 첫 장소가 START가 아닙니다."
            )

        if (
            ordered_place_ids[-1]
            != context.end_place_id
        ):
            raise ValueError(
                "정확 경로 결과의 마지막 장소가 END가 아닙니다."
            )

        ordered_poi_ids = ordered_place_ids[1:-1]

        if len(ordered_poi_ids) != len(
            set(ordered_poi_ids)
        ):
            raise ValueError(
                "정확 경로 결과에 중복 POI가 있습니다."
            )

        expected_poi_ids = set(
            context.poi_place_ids
        )
        actual_poi_ids = set(
            ordered_poi_ids
        )

        missing_poi_ids = sorted(
            expected_poi_ids - actual_poi_ids
        )
        unknown_poi_ids = sorted(
            actual_poi_ids - expected_poi_ids
        )

        if missing_poi_ids:
            raise ValueError(
                "정확 경로 결과에 누락된 POI가 있습니다: "
                + ", ".join(missing_poi_ids)
            )

        if unknown_poi_ids:
            raise ValueError(
                "정확 경로 결과에 알 수 없는 POI가 있습니다: "
                + ", ".join(unknown_poi_ids)
            )

        expected_place_ids = {
            context.start_place_id,
            *context.poi_place_ids,
            context.end_place_id,
        }

        if set(ordered_place_ids) != expected_place_ids:
            raise ValueError(
                "정확 경로 결과의 장소 집합이 입력과 다릅니다."
            )

    # 정확 경로 순서를 RouteStopDTO 목록으로 변환
    def _build_ordered_stops(
        self,
        ordered_place_ids: Tuple[str, ...],
        stops_by_place_id: Mapping[
            str,
            RouteStopDTO,
        ],
    ) -> List[RouteStopDTO]:
        ordered_stops: List[RouteStopDTO] = []

        for place_id in ordered_place_ids:
            stop = stops_by_place_id.get(
                place_id
            )

            if stop is None:
                raise ValueError(
                    "RouteStopDTO를 찾을 수 없습니다: "
                    f"{place_id}"
                )

            ordered_stops.append(stop)

        return ordered_stops

    # 정확 경로의 모든 인접 구간을 RouteLegDTO로 변환
    def _build_route_legs(
        self,
        ordered_place_ids: Tuple[str, ...],
        travel_time_matrix: TravelTimeMatrix,
    ) -> List[RouteLegDTO]:
        route_legs: List[RouteLegDTO] = []

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
                raise ValueError(
                    "정확 경로 결과의 이동 구간이 "
                    "Matrix에 없습니다: "
                    f"{origin_place_id} -> "
                    f"{destination_place_id}"
                )

            route_legs.append(
                RouteLegDTO(
                    origin_place_id=(
                        origin_place_id
                    ),
                    destination_place_id=(
                        destination_place_id
                    ),
                    travel_minutes=travel_minutes,
                )
            )

        return route_legs

    # 경로 구간 합계와 정확 Solver 결과의 비용 교차 검증
    def _validate_route_legs(
        self,
        exact_result: ExactRouteResult,
        route_legs: List[RouteLegDTO],
    ) -> None:
        expected_leg_count = (
            len(exact_result.ordered_place_ids)
            - 1
        )

        if len(route_legs) != expected_leg_count:
            raise ValueError(
                "Route Leg 개수가 경로 구간 수와 다릅니다. "
                f"expected={expected_leg_count}, "
                f"actual={len(route_legs)}"
            )

        route_leg_total = sum(
            route_leg.travel_minutes
            for route_leg in route_legs
        )

        if (
            route_leg_total
            != exact_result.total_travel_minutes
        ):
            raise ValueError(
                "Route Leg 이동시간 합계와 정확 경로 "
                "총 이동시간이 다릅니다. "
                f"route_leg_total={route_leg_total}, "
                "exact_total="
                f"{exact_result.total_travel_minutes}"
            )
