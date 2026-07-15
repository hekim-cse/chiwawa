# Day Assignment 결과의 클러스터링 품질과 배정 품질을 평가하는 모듈
import math
from statistics import pstdev
from typing import Dict, List, Optional, Tuple

from ai.route_planner.domain.trip_schemas import (
    DayPlanDTO,
    PoiDTO,
    TripPlanningRequestDTO,
    TripPlanningResponseDTO,
)
from ai.route_planner.evaluation.schemas import (
    ClusteringEvaluationResultDTO,
    DayClusterEvaluationDTO,
)


# 위도/경도 좌표 타입
Coordinate = Tuple[float, float]


# Day Assignment 결과를 평가하는 클래스
class ClusteringEvaluator:
    # 요청과 실제 Day Assignment 결과를 기반으로 평가 지표 생성
    def evaluate(
        self,
        scenario_id: str,
        request: TripPlanningRequestDTO,
        response: TripPlanningResponseDTO,
    ) -> ClusteringEvaluationResultDTO:
        assigned_day_by_poi_id = (
            self._build_assigned_day_by_poi_id(
                response.day_plans
            )
        )

        assigned_poi_count = len(
            assigned_day_by_poi_id
        )
        unassigned_poi_count = len(
            response.unassigned_pois
        )

        day_clusters = [
            self._evaluate_day_cluster(day_plan)
            for day_plan in response.day_plans
        ]

        poi_counts = [
            cluster.poi_count
            for cluster in day_clusters
        ]
        stay_minutes = [
            cluster.total_stay_minutes
            for cluster in day_clusters
        ]

        return ClusteringEvaluationResultDTO(
            scenario_id=scenario_id,
            silhouette_score=(
                self._calculate_silhouette_score(
                    response.day_plans
                )
            ),
            assignment_rate=self._calculate_rate(
                numerator=assigned_poi_count,
                denominator=len(request.pois),
            ),
            preferred_day_compliance_rate=(
                self._calculate_preferred_day_compliance_rate(
                    request=request,
                    assigned_day_by_poi_id=(
                        assigned_day_by_poi_id
                    ),
                )
            ),
            must_visit_assignment_rate=(
                self._calculate_must_visit_assignment_rate(
                    request=request,
                    assigned_day_by_poi_id=(
                        assigned_day_by_poi_id
                    ),
                )
            ),
            poi_count_stddev=self._calculate_stddev(
                poi_counts
            ),
            stay_minutes_stddev=(
                self._calculate_stddev(
                    stay_minutes
                )
            ),
            assigned_poi_count=assigned_poi_count,
            unassigned_poi_count=(
                unassigned_poi_count
            ),
            day_clusters=day_clusters,
        )

    # POI ID별 실제 배정 day_index 조회 Map 생성
    def _build_assigned_day_by_poi_id(
        self,
        day_plans: List[DayPlanDTO],
    ) -> Dict[str, int]:
        assigned_day_by_poi_id: Dict[str, int] = {}

        for day_plan in day_plans:
            for poi in day_plan.assigned_pois:
                if poi.poi_id in assigned_day_by_poi_id:
                    raise ValueError(
                        "POI가 여러 day에 중복 배정되었습니다: "
                        f"{poi.poi_id}"
                    )

                assigned_day_by_poi_id[poi.poi_id] = (
                    day_plan.day_index
                )

        return assigned_day_by_poi_id

    # 하나의 day 내부 거리 통계 생성
    def _evaluate_day_cluster(
        self,
        day_plan: DayPlanDTO,
    ) -> DayClusterEvaluationDTO:
        pairwise_distances = (
            self._calculate_pairwise_distances(
                day_plan.assigned_pois
            )
        )

        average_distance: Optional[float] = None
        max_distance: Optional[float] = None

        if pairwise_distances:
            average_distance = round(
                sum(pairwise_distances)
                / len(pairwise_distances),
                4,
            )
            max_distance = round(
                max(pairwise_distances),
                4,
            )

        return DayClusterEvaluationDTO(
            day_index=day_plan.day_index,
            assigned_poi_ids=[
                poi.poi_id
                for poi in day_plan.assigned_pois
            ],
            poi_count=len(
                day_plan.assigned_pois
            ),
            total_stay_minutes=(
                day_plan
                .estimated_total_stay_minutes
            ),
            average_intra_cluster_distance_km=(
                average_distance
            ),
            max_intra_cluster_distance_km=(
                max_distance
            ),
        )

    # 같은 day에 포함된 모든 POI 쌍의 거리 계산
    def _calculate_pairwise_distances(
        self,
        pois: List[PoiDTO],
    ) -> List[float]:
        distances: List[float] = []

        for origin_index in range(len(pois)):
            for destination_index in range(
                origin_index + 1,
                len(pois),
            ):
                distances.append(
                    self._haversine_distance_km(
                        origin=(
                            pois[origin_index].lat,
                            pois[origin_index].lng,
                        ),
                        destination=(
                            pois[destination_index].lat,
                            pois[destination_index].lng,
                        ),
                    )
                )

        return distances

    # 전체 배정 결과의 Silhouette Score 계산
    def _calculate_silhouette_score(
        self,
        day_plans: List[DayPlanDTO],
    ) -> Optional[float]:
        non_empty_clusters = [
            day_plan
            for day_plan in day_plans
            if day_plan.assigned_pois
        ]

        assigned_poi_count = sum(
            len(day_plan.assigned_pois)
            for day_plan in non_empty_clusters
        )

        if (
            len(non_empty_clusters) < 2
            or assigned_poi_count < 2
        ):
            return None

        silhouette_values: List[float] = []

        for current_day in non_empty_clusters:
            for poi in current_day.assigned_pois:
                silhouette_values.append(
                    self._calculate_poi_silhouette(
                        poi=poi,
                        current_day=current_day,
                        non_empty_clusters=(
                            non_empty_clusters
                        ),
                    )
                )

        if not silhouette_values:
            return None

        return round(
            sum(silhouette_values)
            / len(silhouette_values),
            4,
        )

    # 하나의 POI에 대한 Silhouette 값 계산
    def _calculate_poi_silhouette(
        self,
        poi: PoiDTO,
        current_day: DayPlanDTO,
        non_empty_clusters: List[DayPlanDTO],
    ) -> float:
        same_cluster_pois = [
            other
            for other in current_day.assigned_pois
            if other.poi_id != poi.poi_id
        ]

        # singleton cluster는 일반적인 정의에 따라 0으로 처리
        if not same_cluster_pois:
            return 0.0

        average_intra_distance = (
            self._calculate_average_distance_to_pois(
                poi=poi,
                other_pois=same_cluster_pois,
            )
        )

        other_cluster_distances = [
            self._calculate_average_distance_to_pois(
                poi=poi,
                other_pois=day_plan.assigned_pois,
            )
            for day_plan in non_empty_clusters
            if day_plan.day_index
            != current_day.day_index
        ]

        if not other_cluster_distances:
            return 0.0

        nearest_other_cluster_distance = min(
            other_cluster_distances
        )

        denominator = max(
            average_intra_distance,
            nearest_other_cluster_distance,
        )

        if denominator == 0:
            return 0.0

        return (
            nearest_other_cluster_distance
            - average_intra_distance
        ) / denominator

    # 특정 POI에서 POI 목록까지의 평균 거리 계산
    def _calculate_average_distance_to_pois(
        self,
        poi: PoiDTO,
        other_pois: List[PoiDTO],
    ) -> float:
        distances = [
            self._haversine_distance_km(
                origin=(poi.lat, poi.lng),
                destination=(
                    other.lat,
                    other.lng,
                ),
            )
            for other in other_pois
        ]

        return sum(distances) / len(distances)

    # preferred_day_index 준수율 계산
    def _calculate_preferred_day_compliance_rate(
        self,
        request: TripPlanningRequestDTO,
        assigned_day_by_poi_id: Dict[str, int],
    ) -> Optional[float]:
        preferred_pois = [
            poi
            for poi in request.pois
            if poi.preferred_day_index is not None
        ]

        if not preferred_pois:
            return None

        compliant_count = sum(
            1
            for poi in preferred_pois
            if assigned_day_by_poi_id.get(
                poi.poi_id
            )
            == poi.preferred_day_index
        )

        return self._calculate_rate(
            numerator=compliant_count,
            denominator=len(preferred_pois),
        )

    # must_visit POI 배정률 계산
    def _calculate_must_visit_assignment_rate(
        self,
        request: TripPlanningRequestDTO,
        assigned_day_by_poi_id: Dict[str, int],
    ) -> Optional[float]:
        must_visit_pois = [
            poi
            for poi in request.pois
            if poi.must_visit
        ]

        if not must_visit_pois:
            return None

        assigned_count = sum(
            1
            for poi in must_visit_pois
            if poi.poi_id
            in assigned_day_by_poi_id
        )

        return self._calculate_rate(
            numerator=assigned_count,
            denominator=len(must_visit_pois),
        )

    # 백분율 계산
    def _calculate_rate(
        self,
        numerator: int,
        denominator: int,
    ) -> float:
        if denominator == 0:
            return 0.0

        return round(
            numerator / denominator * 100,
            4,
        )

    # 모집단 표준편차 계산
    def _calculate_stddev(
        self,
        values: List[int],
    ) -> float:
        if not values:
            return 0.0

        return round(
            pstdev(values),
            4,
        )

    # 두 위도/경도 좌표 사이의 Haversine 거리 계산
    def _haversine_distance_km(
        self,
        origin: Coordinate,
        destination: Coordinate,
    ) -> float:
        earth_radius_km = 6371.0

        origin_lat = math.radians(origin[0])
        origin_lng = math.radians(origin[1])
        destination_lat = math.radians(
            destination[0]
        )
        destination_lng = math.radians(
            destination[1]
        )

        lat_delta = (
            destination_lat - origin_lat
        )
        lng_delta = (
            destination_lng - origin_lng
        )

        haversine_value = (
            math.sin(lat_delta / 2) ** 2
            + math.cos(origin_lat)
            * math.cos(destination_lat)
            * math.sin(lng_delta / 2) ** 2
        )

        central_angle = 2 * math.atan2(
            math.sqrt(haversine_value),
            math.sqrt(1 - haversine_value),
        )

        return earth_radius_km * central_angle
