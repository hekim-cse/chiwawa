# Trip Planning DTO 단위 테스트
import pytest
from pydantic import ValidationError

from ai.route_planner.domain.trip_schemas import (
    PoiCategory,
    TripPlanningRequestDTO,
    TripPlanningResponseDTO,
    TripPlanningStatus,
)


# 정상적인 TripPlanningRequestDTO 샘플을 생성하는 함수
def make_valid_request_payload():
    return {
        "trip_id": "trip_001",
        "timezone": "Asia/Tokyo",
        "days": [
            {
                "day_index": 1,
                "date": "2026-08-01",
                "start_place": {
                    "place_id": "place_start_1",
                    "name": "오사카 난바역",
                    "lat": 34.6657531,
                    "lng": 135.5010362,
                },
                "start_time": "10:00",
                "end_place": {
                    "place_id": "place_end_1",
                    "name": "우메다 스카이빌딩",
                    "lat": 34.7052872,
                    "lng": 135.4896527,
                },
                "end_time": "20:00",
                "max_place_count": 5,
            }
        ],
        "pois": [
            {
                "poi_id": "poi_001",
                "place_id": "google_place_001",
                "name": "도톤보리",
                "lat": 34.6686471,
                "lng": 135.5030983,
                "category": "TOURIST_ATTRACTION",
                "estimated_stay_minutes": 60,
                "priority": 1,
                "must_visit": True,
                "preferred_day_index": None,
            }
        ],
    }


# 요청 DTO가 정상 JSON을 파싱할 수 있는지 검증
def test_trip_planning_request_dto_parses_valid_payload():
    payload = make_valid_request_payload()

    request = TripPlanningRequestDTO.model_validate(payload)

    assert request.trip_id == "trip_001"
    assert request.timezone == "Asia/Tokyo"
    assert len(request.days) == 1
    assert len(request.pois) == 1
    assert request.pois[0].category == PoiCategory.TOURIST_ATTRACTION


# days가 비어 있으면 요청 DTO 검증에 실패하는지 확인
def test_trip_planning_request_rejects_empty_days():
    payload = make_valid_request_payload()
    payload["days"] = []

    with pytest.raises(ValidationError):
        TripPlanningRequestDTO.model_validate(payload)


# pois가 비어 있으면 요청 DTO 검증에 실패하는지 확인
def test_trip_planning_request_rejects_empty_pois():
    payload = make_valid_request_payload()
    payload["pois"] = []

    with pytest.raises(ValidationError):
        TripPlanningRequestDTO.model_validate(payload)


# preferred_day_index가 존재하지 않는 day를 가리키면 검증에 실패하는지 확인
def test_trip_planning_request_rejects_invalid_preferred_day_index():
    payload = make_valid_request_payload()
    payload["pois"][0]["preferred_day_index"] = 99

    with pytest.raises(ValidationError):
        TripPlanningRequestDTO.model_validate(payload)


# 예상 체류 시간이 0 이하이면 검증에 실패하는지 확인
def test_trip_planning_request_rejects_invalid_stay_minutes():
    payload = make_valid_request_payload()
    payload["pois"][0]["estimated_stay_minutes"] = 0

    with pytest.raises(ValidationError):
        TripPlanningRequestDTO.model_validate(payload)


# 응답 DTO가 day별 장소 배정 결과를 표현할 수 있는지 검증
def test_trip_planning_response_dto_parses_valid_payload():
    request_payload = make_valid_request_payload()
    request = TripPlanningRequestDTO.model_validate(request_payload)

    response_payload = {
        "trip_id": request.trip_id,
        "status": "SUCCESS",
        "day_plans": [
            {
                "day_index": 1,
                "date": "2026-08-01",
                "start_place": request.days[0].start_place.model_dump(),
                "end_place": request.days[0].end_place.model_dump(),
                "assigned_pois": [request.pois[0].model_dump()],
                "estimated_total_stay_minutes": 60,
                "assignment_reason": "출발지와 가까운 장소로 Day 1에 배정했습니다.",
            }
        ],
        "unassigned_pois": [],
        "warnings": [],
    }

    response = TripPlanningResponseDTO.model_validate(response_payload)

    assert response.trip_id == "trip_001"
    assert response.status == TripPlanningStatus.SUCCESS
    assert len(response.day_plans) == 1
    assert response.day_plans[0].assigned_pois[0].name == "도톤보리"
