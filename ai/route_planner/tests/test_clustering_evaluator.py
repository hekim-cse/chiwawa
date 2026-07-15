# Day Assignment 클러스터링 평가 단위 테스트
import pytest

from ai.route_planner.domain.trip_schemas import (
    DayPlanDTO,
    TripPlanningRequestDTO,
    TripPlanningResponseDTO,
    TripPlanningStatus,
)
from ai.route_planner.evaluation.clustering_evaluator import (
    ClusteringEvaluator,
)
from ai.route_planner.solvers.day_assignment_solver import (
    DayAssignmentSolver,
)


# 두 지역이 명확히 분리된 Day Assignment 요청 생성
def make_clustering_request_payload():
    return {
        "trip_id": "clustering-evaluation-trip",
        "timezone": "Asia/Tokyo",
        "days": [
            {
                "day_index": 1,
                "date": "2026-08-01",
                "start_place": {
                    "place_id": "day1_start",
                    "name": "지역 A 출발지",
                    "lat": 35.0000,
                    "lng": 135.0000,
                },
                "start_time": "09:00",
                "end_place": {
                    "place_id": "day1_end",
                    "name": "지역 A 도착지",
                    "lat": 35.0000,
                    "lng": 135.0000,
                },
                "end_time": "20:00",
                "max_place_count": 3,
            },
            {
                "day_index": 2,
                "date": "2026-08-02",
                "start_place": {
                    "place_id": "day2_start",
                    "name": "지역 B 출발지",
                    "lat": 36.0000,
                    "lng": 136.0000,
                },
                "start_time": "09:00",
                "end_place": {
                    "place_id": "day2_end",
                    "name": "지역 B 도착지",
                    "lat": 36.0000,
                    "lng": 136.0000,
                },
                "end_time": "20:00",
                "max_place_count": 3,
            },
        ],
        "pois": [
            {
                "poi_id": "poi_a1",
                "place_id": "place_a1",
                "name": "지역 A 장소 1",
                "lat": 35.0010,
                "lng": 135.0010,
                "category": "TOURIST_ATTRACTION",
                "estimated_stay_minutes": 60,
                "priority": 1,
                "must_visit": True,
                "preferred_day_index": 1,
            },
            {
                "poi_id": "poi_a2",
                "place_id": "place_a2",
                "name": "지역 A 장소 2",
                "lat": 35.0020,
                "lng": 135.0020,
                "category": "CAFE",
                "estimated_stay_minutes": 90,
                "priority": 2,
                "must_visit": True,
                "preferred_day_index": None,
            },
            {
                "poi_id": "poi_b1",
                "place_id": "place_b1",
                "name": "지역 B 장소 1",
                "lat": 36.0010,
                "lng": 136.0010,
                "category": "SHOPPING",
                "estimated_stay_minutes": 60,
                "priority": 1,
                "must_visit": True,
                "preferred_day_index": 2,
            },
            {
                "poi_id": "poi_b2",
                "place_id": "place_b2",
                "name": "지역 B 장소 2",
                "lat": 36.0020,
                "lng": 136.0020,
                "category": "RESTAURANT",
                "estimated_stay_minutes": 90,
                "priority": 2,
                "must_visit": False,
                "preferred_day_index": None,
            },
        ],
    }


# Solver 실행 후 Clustering Evaluation 결과 생성
def evaluate_request(payload):
    request = TripPlanningRequestDTO.model_validate(payload)
    response = DayAssignmentSolver().assign_pois_to_days(request)

    result = ClusteringEvaluator().evaluate(
        scenario_id="clustering-evaluation-001",
        request=request,
        response=response,
    )

    return request, response, result


# 명확히 분리된 두 지역의 배정 및 클러스터링 품질 평가
def test_evaluate_well_separated_day_clusters():
    _, response, result = evaluate_request(
        make_clustering_request_payload()
    )

    assert response.status == TripPlanningStatus.SUCCESS

    assert result.scenario_id == "clustering-evaluation-001"
    assert result.assigned_poi_count == 4
    assert result.unassigned_poi_count == 0
    assert result.assignment_rate == 100.0
    assert result.preferred_day_compliance_rate == 100.0
    assert result.must_visit_assignment_rate == 100.0

    assert result.silhouette_score is not None
    assert result.silhouette_score > 0.9

    assert result.poi_count_stddev == 0.0
    assert result.stay_minutes_stddev == 0.0

    assert len(result.day_clusters) == 2

    for day_cluster in result.day_clusters:
        assert day_cluster.poi_count == 2
        assert day_cluster.total_stay_minutes == 150

        assert (
            day_cluster.average_intra_cluster_distance_km
            is not None
        )
        assert (
            day_cluster.max_intra_cluster_distance_km
            is not None
        )
        assert (
            day_cluster.average_intra_cluster_distance_km
            > 0
        )
        assert (
            day_cluster.max_intra_cluster_distance_km
            > 0
        )


# day 수용량 부족 시 전체 배정률과 must_visit 배정률 감소 검증
def test_evaluate_assignment_rate_when_day_capacity_is_insufficient():
    payload = make_clustering_request_payload()
    payload["days"][0]["max_place_count"] = 1
    payload["days"][1]["max_place_count"] = 1

    _, response, result = evaluate_request(payload)

    assert response.status == TripPlanningStatus.PARTIAL_SUCCESS

    assert result.assigned_poi_count == 2
    assert result.unassigned_poi_count == 2
    assert result.assignment_rate == 50.0

    # preferred POI는 일반 POI보다 먼저 배정되므로 모두 준수
    assert result.preferred_day_compliance_rate == 100.0

    # must_visit POI 3개 중 preferred POI 2개만 배정
    assert result.must_visit_assignment_rate == pytest.approx(
        66.6667
    )

    # 두 day 모두 한 개씩 배정되므로 개수 편차 없음
    assert result.poi_count_stddev == 0.0

    # 두 day 모두 60분짜리 preferred POI가 배정
    assert result.stay_minutes_stddev == 0.0


# preferred_day가 지정된 POI가 없으면 준수율을 계산하지 않음
def test_preferred_day_compliance_rate_is_none_without_preference():
    payload = make_clustering_request_payload()

    for poi in payload["pois"]:
        poi["preferred_day_index"] = None

    _, _, result = evaluate_request(payload)

    assert result.preferred_day_compliance_rate is None


# must_visit POI가 없으면 must_visit 배정률을 계산하지 않음
def test_must_visit_assignment_rate_is_none_without_must_visit_pois():
    payload = make_clustering_request_payload()

    for poi in payload["pois"]:
        poi["must_visit"] = False

    _, _, result = evaluate_request(payload)

    assert result.must_visit_assignment_rate is None


# day가 하나뿐이면 Silhouette Score를 계산하지 않음
def test_silhouette_score_is_none_with_single_day():
    payload = make_clustering_request_payload()
    payload["days"] = [payload["days"][0]]

    for poi in payload["pois"]:
        poi["preferred_day_index"] = None

    payload["days"][0]["max_place_count"] = 4

    _, response, result = evaluate_request(payload)

    assert response.status == TripPlanningStatus.SUCCESS
    assert result.assignment_rate == 100.0
    assert result.silhouette_score is None
    assert len(result.day_clusters) == 1


# 각 day에 POI가 하나씩 있으면 singleton silhouette을 0으로 처리
def test_silhouette_score_is_zero_with_singleton_clusters():
    payload = make_clustering_request_payload()
    payload["pois"] = [
        payload["pois"][0],
        payload["pois"][2],
    ]

    _, response, result = evaluate_request(payload)

    assert response.status == TripPlanningStatus.SUCCESS
    assert result.silhouette_score == 0.0

    for day_cluster in result.day_clusters:
        assert day_cluster.poi_count == 1
        assert (
            day_cluster.average_intra_cluster_distance_km
            is None
        )
        assert (
            day_cluster.max_intra_cluster_distance_km
            is None
        )


# 동일 POI가 여러 day에 포함된 비정상 응답 거부
def test_reject_duplicate_poi_assignment_across_days():
    request = TripPlanningRequestDTO.model_validate(
        make_clustering_request_payload()
    )
    normal_response = (
        DayAssignmentSolver().assign_pois_to_days(request)
    )

    duplicate_poi = normal_response.day_plans[
        0
    ].assigned_pois[0]

    duplicated_day_plans = [
        day_plan.model_copy(deep=True)
        for day_plan in normal_response.day_plans
    ]
    duplicated_day_plans[1] = duplicated_day_plans[
        1
    ].model_copy(
        update={
            "assigned_pois": [
                *duplicated_day_plans[1].assigned_pois,
                duplicate_poi,
            ],
            "estimated_total_stay_minutes": (
                duplicated_day_plans[
                    1
                ].estimated_total_stay_minutes
                + duplicate_poi.estimated_stay_minutes
            ),
        }
    )

    invalid_response = TripPlanningResponseDTO(
        trip_id=normal_response.trip_id,
        status=normal_response.status,
        day_plans=duplicated_day_plans,
        unassigned_pois=normal_response.unassigned_pois,
        warnings=normal_response.warnings,
    )

    with pytest.raises(
        ValueError,
        match="여러 day에 중복 배정",
    ):
        ClusteringEvaluator().evaluate(
            scenario_id="duplicate-assignment",
            request=request,
            response=invalid_response,
        )
