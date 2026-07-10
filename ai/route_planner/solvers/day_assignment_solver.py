# TripPlanningRequestDTO를 기반으로 POI를 day별로 자동 분배하는 Solver
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    DayPlanDTO,
    PoiDTO,
    TripPlanningRequestDTO,
    TripPlanningResponseDTO,
    TripPlanningStatus,
    UnassignedPoiDTO,
)


# 위도/경도 좌표 타입
Coordinate = Tuple[float, float]


# K-means 클러스터링 결과 타입
# key는 day 번호가 아닌 클러스터 번호
ClusterMap = Dict[int, List[PoiDTO]]


# Day Assignment Solver 설정값
@dataclass(frozen=True)
class DayAssignmentSolverConfig:
    # K-means 반복 최대 횟수
    max_kmeans_iterations: int = 20

    # 하루 일정에서 체류 시간만으로도 사용 가능 시간을 초과할 때 경고를 표시할지 여부
    warn_when_stay_time_exceeds_available_time: bool = True


# POI를 여행 day별로 분배하는 Solver
class DayAssignmentSolver:
    # DayAssignmentSolver 생성자
    # config: K-means 반복 횟수와 경고 정책 등을 담은 설정값
    def __init__(self, config: Optional[DayAssignmentSolverConfig] = None):
        self.config = config or DayAssignmentSolverConfig()

    # TripPlanningRequestDTO를 받아 day별 POI 배정 결과를 반환하는 함수
    # request: 백엔드에서 전달받은 여행 일정 최적화 요청 DTO
    # 반환: day별 POI 배정 결과를 담은 TripPlanningResponseDTO
    def assign_pois_to_days(
        self,
        request: TripPlanningRequestDTO,
    ) -> TripPlanningResponseDTO:
        assigned_by_day: Dict[int, List[PoiDTO]] = {
            day.day_index: []
            for day in request.days
        }
        unassigned_pois: List[UnassignedPoiDTO] = []
        warnings: List[str] = []

        remaining_pois = self._assign_preferred_day_pois(
            pois=request.pois,
            days=request.days,
            assigned_by_day=assigned_by_day,
            unassigned_pois=unassigned_pois,
        )

        self._assign_remaining_pois_by_clustering(
            pois=remaining_pois,
            days=request.days,
            assigned_by_day=assigned_by_day,
            unassigned_pois=unassigned_pois,
        )

        day_plans = self._build_day_plans(
            days=request.days,
            assigned_by_day=assigned_by_day,
            warnings=warnings,
        )

        status = self._resolve_status(
            day_plans=day_plans,
            unassigned_pois=unassigned_pois,
        )

        return TripPlanningResponseDTO(
            trip_id=request.trip_id,
            status=status,
            day_plans=day_plans,
            unassigned_pois=unassigned_pois,
            warnings=warnings,
        )

    # preferred_day_index가 지정된 POI를 우선 배정하는 함수
    # preferred_day_index가 없는 POI는 remaining_pois로 반환
    def _assign_preferred_day_pois(
        self,
        pois: List[PoiDTO],
        days: List[DayConstraintDTO],
        assigned_by_day: Dict[int, List[PoiDTO]],
        unassigned_pois: List[UnassignedPoiDTO],
    ) -> List[PoiDTO]:
        day_by_index = {
            day.day_index: day
            for day in days
        }
        remaining_pois: List[PoiDTO] = []

        for poi in pois:
            if poi.preferred_day_index is None:
                remaining_pois.append(poi)
                continue

            target_day = day_by_index[poi.preferred_day_index]

            if not self._has_day_capacity(
                day=target_day,
                assigned_pois=assigned_by_day[target_day.day_index],
            ):
                unassigned_pois.append(
                    UnassignedPoiDTO(
                        poi=poi,
                        reason=(
                            f"preferred_day_index={poi.preferred_day_index}의 "
                            "max_place_count를 초과하여 배정할 수 없습니다."
                        ),
                    )
                )
                continue

            assigned_by_day[target_day.day_index].append(poi)

        return remaining_pois

    # preferred_day_index가 없는 POI를 K-means 클러스터링 기반으로 day에 배정하는 함수
    def _assign_remaining_pois_by_clustering(
        self,
        pois: List[PoiDTO],
        days: List[DayConstraintDTO],
        assigned_by_day: Dict[int, List[PoiDTO]],
        unassigned_pois: List[UnassignedPoiDTO],
    ) -> None:
        if not pois:
            return

        cluster_count = min(len(days), len(pois))
        clusters = self._cluster_pois_by_kmeans(
            pois=pois,
            cluster_count=cluster_count,
        )

        for cluster_pois in clusters.values():
            target_day = self._find_best_day_for_cluster(
                cluster_pois=cluster_pois,
                days=days,
                assigned_by_day=assigned_by_day,
            )

            for poi in cluster_pois:
                if target_day is None:
                    unassigned_pois.append(
                        UnassignedPoiDTO(
                            poi=poi,
                            reason="배정 가능한 day가 없어 미배정 처리되었습니다.",
                        )
                    )
                    continue

                if not self._has_day_capacity(
                    day=target_day,
                    assigned_pois=assigned_by_day[target_day.day_index],
                ):
                    unassigned_pois.append(
                        UnassignedPoiDTO(
                            poi=poi,
                            reason=(
                                f"Day {target_day.day_index}의 max_place_count를 "
                                "초과하여 배정할 수 없습니다."
                            ),
                        )
                    )
                    continue

                assigned_by_day[target_day.day_index].append(poi)

    # 좌표 기반 K-means로 POI를 클러스터링하는 함수
    # K-means는 day별 초기 장소 묶음을 만들기 위한 용도로만 사용
    def _cluster_pois_by_kmeans(
        self,
        pois: List[PoiDTO],
        cluster_count: int,
    ) -> ClusterMap:
        if cluster_count <= 0:
            return {}

        if cluster_count == 1:
            return {0: pois}

        centroids = self._initialize_centroids(
            pois=pois,
            cluster_count=cluster_count,
        )

        clusters: ClusterMap = {}

        for _ in range(self.config.max_kmeans_iterations):
            clusters = self._assign_pois_to_nearest_centroid(
                pois=pois,
                centroids=centroids,
            )
            next_centroids = self._recalculate_centroids(
                clusters=clusters,
                previous_centroids=centroids,
            )

            if next_centroids == centroids:
                break

            centroids = next_centroids

        return clusters

    # 초기 중심점을 결정하는 함수
    # 랜덤을 사용하지 않고 POI 순서를 기반으로 결정해 테스트 결과가 매번 동일하도록 구성
    def _initialize_centroids(
        self,
        pois: List[PoiDTO],
        cluster_count: int,
    ) -> List[Coordinate]:
        sorted_pois = sorted(pois, key=lambda poi: poi.poi_id)

        if cluster_count == 1:
            selected_pois = [sorted_pois[0]]
        else:
            selected_pois = [
                sorted_pois[
                    round(index * (len(sorted_pois) - 1) / (cluster_count - 1))
                ]
                for index in range(cluster_count)
            ]

        return [
            (poi.lat, poi.lng)
            for poi in selected_pois
        ]

    # 각 POI를 가장 가까운 중심점에 배정하는 함수
    def _assign_pois_to_nearest_centroid(
        self,
        pois: List[PoiDTO],
        centroids: List[Coordinate],
    ) -> ClusterMap:
        clusters: ClusterMap = {
            cluster_index: []
            for cluster_index in range(len(centroids))
        }

        for poi in pois:
            nearest_cluster_index = min(
                range(len(centroids)),
                key=lambda cluster_index: self._haversine_minutes_proxy(
                    origin=(poi.lat, poi.lng),
                    destination=centroids[cluster_index],
                ),
            )
            clusters[nearest_cluster_index].append(poi)

        return clusters

    # 클러스터에 배정된 POI들의 평균 좌표로 중심점을 다시 계산하는 함수
    def _recalculate_centroids(
        self,
        clusters: ClusterMap,
        previous_centroids: List[Coordinate],
    ) -> List[Coordinate]:
        next_centroids: List[Coordinate] = []

        for cluster_index, cluster_pois in clusters.items():
            if not cluster_pois:
                next_centroids.append(previous_centroids[cluster_index])
                continue

            average_lat = sum(poi.lat for poi in cluster_pois) / len(cluster_pois)
            average_lng = sum(poi.lng for poi in cluster_pois) / len(cluster_pois)

            next_centroids.append((average_lat, average_lng))

        return next_centroids

    # 하나의 클러스터를 어떤 day에 배정할지 결정하는 함수
    # 클러스터 중심점과 day 출발지/도착지의 평균 접근 거리가 가장 짧은 day를 선택
    def _find_best_day_for_cluster(
        self,
        cluster_pois: List[PoiDTO],
        days: List[DayConstraintDTO],
        assigned_by_day: Dict[int, List[PoiDTO]],
    ) -> Optional[DayConstraintDTO]:
        if not cluster_pois:
            return None

        cluster_center = self._calculate_cluster_center(cluster_pois)

        candidate_days = [
            day
            for day in days
            if self._has_day_capacity(
                day=day,
                assigned_pois=assigned_by_day[day.day_index],
            )
        ]

        if not candidate_days:
            return None

        return min(
            candidate_days,
            key=lambda day: self._calculate_day_access_score(
                cluster_center=cluster_center,
                day=day,
            ),
        )

    # 클러스터 중심점을 계산하는 함수
    def _calculate_cluster_center(
        self,
        pois: List[PoiDTO],
    ) -> Coordinate:
        average_lat = sum(poi.lat for poi in pois) / len(pois)
        average_lng = sum(poi.lng for poi in pois) / len(pois)

        return average_lat, average_lng

    # 클러스터 중심점과 day 출발지/도착지의 접근성 점수를 계산하는 함수
    # 값이 낮을수록 해당 day 조건에 더 가까운 클러스터로 판단
    def _calculate_day_access_score(
        self,
        cluster_center: Coordinate,
        day: DayConstraintDTO,
    ) -> float:
        start_distance = self._haversine_minutes_proxy(
            origin=cluster_center,
            destination=(day.start_place.lat, day.start_place.lng),
        )
        end_distance = self._haversine_minutes_proxy(
            origin=cluster_center,
            destination=(day.end_place.lat, day.end_place.lng),
        )

        return start_distance + end_distance

    # day의 max_place_count를 초과하지 않는지 확인하는 함수
    def _has_day_capacity(
        self,
        day: DayConstraintDTO,
        assigned_pois: List[PoiDTO],
    ) -> bool:
        if day.max_place_count is None:
            return True

        return len(assigned_pois) < day.max_place_count

    # DayPlanDTO 목록을 생성하는 함수
    def _build_day_plans(
        self,
        days: List[DayConstraintDTO],
        assigned_by_day: Dict[int, List[PoiDTO]],
        warnings: List[str],
    ) -> List[DayPlanDTO]:
        day_plans: List[DayPlanDTO] = []

        for day in days:
            assigned_pois = assigned_by_day[day.day_index]
            estimated_total_stay_minutes = sum(
                poi.estimated_stay_minutes
                for poi in assigned_pois
            )

            available_minutes = self._calculate_available_minutes(day)

            if (
                self.config.warn_when_stay_time_exceeds_available_time
                and available_minutes is not None
                and estimated_total_stay_minutes > available_minutes
            ):
                warnings.append(
                    f"Day {day.day_index}의 예상 체류 시간 합이 사용 가능 시간을 초과합니다. "
                    f"stay={estimated_total_stay_minutes}분, available={available_minutes}분"
                )

            day_plans.append(
                DayPlanDTO(
                    day_index=day.day_index,
                    date=day.date,
                    start_place=day.start_place,
                    end_place=day.end_place,
                    assigned_pois=assigned_pois,
                    estimated_total_stay_minutes=estimated_total_stay_minutes,
                    assignment_reason=self._build_assignment_reason(
                        day=day,
                        assigned_pois=assigned_pois,
                    ),
                )
            )

        return day_plans

    # day별 배정 사유 문구를 생성하는 함수
    def _build_assignment_reason(
        self,
        day: DayConstraintDTO,
        assigned_pois: List[PoiDTO],
    ) -> str:
        if not assigned_pois:
            return f"Day {day.day_index}에 배정된 POI가 없습니다."

        return (
            f"Day {day.day_index}의 출발지/도착지 접근성과 "
            "장소 클러스터링 결과를 기준으로 배정했습니다."
        )

    # 응답 상태를 결정하는 함수
    def _resolve_status(
        self,
        day_plans: List[DayPlanDTO],
        unassigned_pois: List[UnassignedPoiDTO],
    ) -> TripPlanningStatus:
        if not day_plans:
            return TripPlanningStatus.FAILED

        if unassigned_pois:
            return TripPlanningStatus.PARTIAL_SUCCESS

        return TripPlanningStatus.SUCCESS

    # HH:MM 문자열을 분 단위로 변환하는 함수
    # 형식이 맞지 않으면 None을 반환해 경고 검증에서 제외
    def _parse_time_to_minutes(self, raw_time: str) -> Optional[int]:
        try:
            hour_text, minute_text = raw_time.split(":")
            hour = int(hour_text)
            minute = int(minute_text)
        except ValueError:
            return None

        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return None

        return hour * 60 + minute

    # day의 사용 가능 시간을 분 단위로 계산하는 함수
    def _calculate_available_minutes(
        self,
        day: DayConstraintDTO,
    ) -> Optional[int]:
        start_minutes = self._parse_time_to_minutes(day.start_time)
        end_minutes = self._parse_time_to_minutes(day.end_time)

        if start_minutes is None or end_minutes is None:
            return None

        if end_minutes < start_minutes:
            return None

        return end_minutes - start_minutes

    # 두 좌표 간 거리를 계산하는 함수
    # 실제 이동 시간은 아니며, day clustering과 접근성 점수 계산용 거리 proxy로만 사용
    def _haversine_minutes_proxy(
        self,
        origin: Coordinate,
        destination: Coordinate,
    ) -> float:
        earth_radius_km = 6371.0

        origin_lat, origin_lng = origin
        destination_lat, destination_lng = destination

        lat_delta = math.radians(destination_lat - origin_lat)
        lng_delta = math.radians(destination_lng - origin_lng)

        origin_lat_rad = math.radians(origin_lat)
        destination_lat_rad = math.radians(destination_lat)

        a = (
            math.sin(lat_delta / 2) ** 2
            + math.cos(origin_lat_rad)
            * math.cos(destination_lat_rad)
            * math.sin(lng_delta / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return earth_radius_km * c
