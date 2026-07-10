# DayPlanDTO를 기반으로 day 내부 방문 순서를 생성하는 Route Option Solver
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from ai.route_planner.domain.schemas import TravelMode, TravelTimeMatrix
from ai.route_planner.domain.trip_schemas import (
    DayPlanDTO,
    PoiDTO,
    RouteLegDTO,
    RouteOptionDTO,
    RouteStopDTO,
    RouteStopType,
)


# Route Option Solver 설정값
@dataclass(frozen=True)
class RouteOptionSolverConfig:
    # Local Search 반복 최대 횟수
    max_local_search_iterations: int = 50


# 방문 순서 계산 중 내부에서 사용하는 정류장 정보
# Solver 내부에서는 출발지, POI, 도착지를 모두 같은 형태로 다루는 게 편하기 때문
@dataclass(frozen=True)
class RouteNode:
    stop_type: RouteStopType
    place_id: str
    name: str
    lat: float
    lng: float


# day별 POI 방문 순서를 생성하는 Solver
class RouteOptionSolver:
    # config: Local Search 반복 횟수 등 Solver 동작 설정
    def __init__(self, config: Optional[RouteOptionSolverConfig] = None):
        self.config = config or RouteOptionSolverConfig()

    # DayPlanDTO와 이동 시간 행렬을 기반으로 하나의 경로 옵션을 생성하는 함수
    def solve_route_option(
        self,
        day_plan: DayPlanDTO,   # Day Assignment Solver에서 생성된 day별 POI 배정 결과
        travel_mode: TravelMode,
        travel_time_matrix: TravelTimeMatrix,
    ) -> RouteOptionDTO:    # RouteOptionDTO: 최종 방문 순서와 이동 구간을 담은 DTO
        start_node = self._build_start_node(day_plan)
        end_node = self._build_end_node(day_plan)
        poi_nodes = [
            self._build_poi_node(poi)
            for poi in day_plan.assigned_pois
        ]

        missing_segments: Set[str] = set()
        warnings: List[str] = []

        if not poi_nodes:
            route_nodes = [start_node, end_node]
            total_minutes = self._calculate_route_total_minutes(
                route_nodes=route_nodes,
                travel_time_matrix=travel_time_matrix,
                missing_segments=missing_segments,
            )

            if total_minutes is None:
                warnings.append("출발지에서 도착지까지의 이동 시간 정보가 없어 경로 시간을 계산할 수 없습니다.")
                total_minutes = 0

            return self._build_route_option(
                day_index=day_plan.day_index,
                travel_mode=travel_mode,
                route_nodes=route_nodes,
                total_travel_minutes=total_minutes,
                travel_time_matrix=travel_time_matrix,
                missing_segments=missing_segments,
                warnings=warnings,
            )
        
        # POI가 있는 경우 Cheapest Insertion + Local Search를 통해 경로를 생성
        route_nodes, uninserted_nodes = self._build_initial_route_by_cheapest_insertion(
            start_node=start_node,
            end_node=end_node,
            poi_nodes=poi_nodes,
            travel_time_matrix=travel_time_matrix,
            missing_segments=missing_segments,
        )

        # 이동 시간 행렬이 부족해서 어떤 POI를 어디에도 넣을 수 없으면 uninserted_nodes에 남게 됨
        if uninserted_nodes:
            warnings.append(
                "일부 POI는 필요한 이동 시간 구간이 부족해 경로에 포함하지 못했습니다: "
                + ", ".join(node.place_id for node in uninserted_nodes)
            )

        # Local Search를 통해 경로를 개선
        route_nodes = self._improve_route_by_local_search(
            route_nodes=route_nodes,
            travel_time_matrix=travel_time_matrix,
            missing_segments=missing_segments,
        )

        # 최종 경로의 총 이동 시간을 계산
        total_minutes = self._calculate_route_total_minutes(
            route_nodes=route_nodes,
            travel_time_matrix=travel_time_matrix,
            missing_segments=missing_segments,
        )

        if total_minutes is None:
            warnings.append("최종 경로의 일부 이동 시간 정보가 없어 총 이동 시간을 계산할 수 없습니다.")
            total_minutes = 0

        return self._build_route_option(
            day_index=day_plan.day_index,
            travel_mode=travel_mode,
            route_nodes=route_nodes,
            total_travel_minutes=total_minutes,
            travel_time_matrix=travel_time_matrix,
            missing_segments=missing_segments,
            warnings=warnings,
        )

    # Cheapest Insertion 방식으로 초기 경로를 생성하는 함수
    # start → end 경로에 POI를 하나씩 가장 비용 증가가 적은 위치에 삽입
    def _build_initial_route_by_cheapest_insertion(
        self,
        start_node: RouteNode,
        end_node: RouteNode,
        poi_nodes: List[RouteNode],
        travel_time_matrix: TravelTimeMatrix,
        missing_segments: Set[str],
    ) -> Tuple[List[RouteNode], List[RouteNode]]:
        route_nodes = [start_node, end_node]
        remaining_nodes = list(poi_nodes)
        uninserted_nodes: List[RouteNode] = []

        while remaining_nodes:
            best_candidate_route: Optional[List[RouteNode]] = None
            best_candidate_node: Optional[RouteNode] = None
            best_candidate_total: Optional[int] = None

            for node in remaining_nodes:
                for insert_index in range(1, len(route_nodes)):
                    candidate_route = (
                        route_nodes[:insert_index]
                        + [node]
                        + route_nodes[insert_index:]
                    )
                    candidate_total = self._calculate_route_total_minutes(
                        route_nodes=candidate_route,
                        travel_time_matrix=travel_time_matrix,
                        missing_segments=missing_segments,
                    )

                    if candidate_total is None:
                        continue
                    
                    # 현재까지 가장 비용 증가가 적은 후보 경로를 갱신
                    if (
                        best_candidate_total is None
                        or candidate_total < best_candidate_total
                    ):
                        best_candidate_total = candidate_total
                        best_candidate_node = node
                        best_candidate_route = candidate_route
        
            if best_candidate_route is None or best_candidate_node is None:
                uninserted_nodes.extend(remaining_nodes)
                break

            route_nodes = best_candidate_route
            remaining_nodes.remove(best_candidate_node)

        return route_nodes, uninserted_nodes

    # Relocate와 2-opt를 반복 적용해 경로를 개선하는 함수
    def _improve_route_by_local_search(
        self,
        route_nodes: List[RouteNode],
        travel_time_matrix: TravelTimeMatrix,
        missing_segments: Set[str],
    ) -> List[RouteNode]:
        current_route = route_nodes

        for _ in range(self.config.max_local_search_iterations):
            relocated_route = self._improve_route_by_relocate(
                route_nodes=current_route,
                travel_time_matrix=travel_time_matrix,
                missing_segments=missing_segments,
            )

            two_opt_route = self._improve_route_by_two_opt(
                route_nodes=relocated_route,
                travel_time_matrix=travel_time_matrix,
                missing_segments=missing_segments,
            )

            if two_opt_route == current_route:
                break

            current_route = two_opt_route

        return current_route

    # POI 하나의 위치를 다른 위치로 옮겨 경로가 짧아지는지 확인하는 함수
    def _improve_route_by_relocate(
        self,
        route_nodes: List[RouteNode],
        travel_time_matrix: TravelTimeMatrix,
        missing_segments: Set[str],
    ) -> List[RouteNode]:
        best_route = route_nodes
        best_total = self._calculate_route_total_minutes(
            route_nodes=best_route,
            travel_time_matrix=travel_time_matrix,
            missing_segments=missing_segments,
        )

        if best_total is None:
            return route_nodes

        for source_index in range(1, len(route_nodes) - 1):
            node = route_nodes[source_index]
            route_without_node = (
                route_nodes[:source_index]
                + route_nodes[source_index + 1:]
            )

            for insert_index in range(1, len(route_without_node)):
                candidate_route = (
                    route_without_node[:insert_index]
                    + [node]
                    + route_without_node[insert_index:]
                )
                candidate_total = self._calculate_route_total_minutes(
                    route_nodes=candidate_route,
                    travel_time_matrix=travel_time_matrix,
                    missing_segments=missing_segments,
                )

                if candidate_total is None:
                    continue

                if candidate_total < best_total:
                    best_total = candidate_total
                    best_route = candidate_route

        return best_route

    # 경로의 중간 구간을 뒤집어 경로가 짧아지는지 확인하는 함수
    def _improve_route_by_two_opt(
        self,
        route_nodes: List[RouteNode],
        travel_time_matrix: TravelTimeMatrix,
        missing_segments: Set[str],
    ) -> List[RouteNode]:
        best_route = route_nodes
        best_total = self._calculate_route_total_minutes(
            route_nodes=best_route,
            travel_time_matrix=travel_time_matrix,
            missing_segments=missing_segments,
        )

        if best_total is None:
            return route_nodes

        for start_index in range(1, len(route_nodes) - 2):
            for end_index in range(start_index + 1, len(route_nodes) - 1):
                candidate_route = (
                    route_nodes[:start_index]
                    + list(reversed(route_nodes[start_index:end_index + 1]))
                    + route_nodes[end_index + 1:]
                )
                candidate_total = self._calculate_route_total_minutes(
                    route_nodes=candidate_route,
                    travel_time_matrix=travel_time_matrix,
                    missing_segments=missing_segments,
                )

                if candidate_total is None:
                    continue

                if candidate_total < best_total:
                    best_total = candidate_total
                    best_route = candidate_route

        return best_route

    # 경로 전체 이동 시간을 계산하는 함수
    # 이동 시간 행렬에 없는 구간이 있으면 None을 반환하고 missing_segments에 기록
    def _calculate_route_total_minutes(
        self,
        route_nodes: List[RouteNode],
        travel_time_matrix: TravelTimeMatrix,
        missing_segments: Set[str],
    ) -> Optional[int]:
        total_minutes = 0

        for origin_node, destination_node in zip(route_nodes, route_nodes[1:]):
            travel_minutes = self._get_travel_minutes(
                origin_place_id=origin_node.place_id,
                destination_place_id=destination_node.place_id,
                travel_time_matrix=travel_time_matrix,
                missing_segments=missing_segments,
            )

            if travel_minutes is None:
                return None

            total_minutes += travel_minutes

        return total_minutes

    # 이동 시간 행렬에서 두 장소 간 이동 시간을 조회하는 함수
    def _get_travel_minutes(
        self,
        origin_place_id: str,
        destination_place_id: str,
        travel_time_matrix: TravelTimeMatrix,
        missing_segments: Set[str],
    ) -> Optional[int]:
        key = (origin_place_id, destination_place_id)

        if key not in travel_time_matrix:
            missing_segments.add(f"{origin_place_id} -> {destination_place_id}")
            return None

        return travel_time_matrix[key]

    # RouteOptionDTO를 생성하는 함수
    def _build_route_option(
        self,
        day_index: int,
        travel_mode: TravelMode,
        route_nodes: List[RouteNode],
        total_travel_minutes: int,
        travel_time_matrix: TravelTimeMatrix,
        missing_segments: Set[str],
        warnings: List[str],
    ) -> RouteOptionDTO:
        route_legs: List[RouteLegDTO] = []

        for origin_node, destination_node in zip(route_nodes, route_nodes[1:]):
            travel_minutes = travel_time_matrix.get(
                (origin_node.place_id, destination_node.place_id)
            )

            if travel_minutes is None:
                continue

            route_legs.append(
                RouteLegDTO(
                    origin_place_id=origin_node.place_id,
                    destination_place_id=destination_node.place_id,
                    travel_minutes=travel_minutes,
                )
            )

        return RouteOptionDTO(
            day_index=day_index,
            travel_mode=travel_mode,
            total_travel_minutes=total_travel_minutes,
            ordered_stops=[
                RouteStopDTO(
                    stop_type=node.stop_type,
                    place_id=node.place_id,
                    name=node.name,
                    lat=node.lat,
                    lng=node.lng,
                )
                for node in route_nodes
            ],
            route_legs=route_legs,
            missing_segments=sorted(missing_segments),
            warnings=warnings,
        )

    # DayPlanDTO의 출발지를 RouteNode로 변환하는 함수
    def _build_start_node(self, day_plan: DayPlanDTO) -> RouteNode:
        return RouteNode(
            stop_type=RouteStopType.START,
            place_id=day_plan.start_place.place_id,
            name=day_plan.start_place.name,
            lat=day_plan.start_place.lat,
            lng=day_plan.start_place.lng,
        )

    # DayPlanDTO의 도착지를 RouteNode로 변환하는 함수
    def _build_end_node(self, day_plan: DayPlanDTO) -> RouteNode:
        return RouteNode(
            stop_type=RouteStopType.END,
            place_id=day_plan.end_place.place_id,
            name=day_plan.end_place.name,
            lat=day_plan.end_place.lat,
            lng=day_plan.end_place.lng,
        )

    # PoiDTO를 RouteNode로 변환하는 함수
    def _build_poi_node(self, poi: PoiDTO) -> RouteNode:
        return RouteNode(
            stop_type=RouteStopType.POI,
            place_id=poi.place_id,
            name=poi.name,
            lat=poi.lat,
            lng=poi.lng,
        )
