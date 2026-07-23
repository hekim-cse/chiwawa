# Modal 통합 응답(일정 최적화 + 추천) 계약 검증 테스트
#   cd backend && uv run pytest tests/test_ai_planning_recommendations_contract.py

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from chiwawa_backend.schemas.ai_planning import (
    RecommendationStatus,
    TripPlanningStatus,
    TripPlanningWithRecommendationsResponse,
)

FIXTURE = Path(__file__).parent / "fixtures" / "modal_plan_trip_with_recommendations.json"


def _payload() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parses_full_integration_contract() -> None:
    # Given: include_recommendations=true 통합 응답 fixture.
    parsed = TripPlanningWithRecommendationsResponse.model_validate(_payload())

    # Then: 최상위 + 중첩 구조가 모두 파싱된다.
    assert parsed.status is TripPlanningStatus.PARTIAL_SUCCESS
    day = parsed.day_plans[0]
    assert day.route_options[0].travel_mode == "DRIVE"
    assert day.route_options[0].timeline is not None
    assert day.route_options[0].timeline.timeline_stops[0].stop_type == "START"
    # timeline == null 인 route_option 은 그대로 유지된다.
    assert day.route_options[1].timeline is None
    assert day.route_options[1].missing_segments == ["ChIJ_fmKgRPnAGARkKWLtCYTu7g"]

    rec_day = parsed.day_recommendations[0]
    ok = rec_day.route_options[0]
    assert ok.status is RecommendationStatus.SUCCESS
    assert ok.recommendation is not None
    group = ok.recommendation.recommendation_groups[0]
    assert group.category == "CAFE"
    candidate = group.recommendations[0]
    assert candidate.candidate.rating == pytest.approx(4.1)
    assert candidate.insertion_impact.additional_minutes == 34
    assert candidate.window.leg_index == 0

    # UNAVAILABLE 은 recommendation 이 null 이고 원본 route_option 은 유지된다.
    unavailable = rec_day.route_options[1]
    assert unavailable.status is RecommendationStatus.UNAVAILABLE
    assert unavailable.recommendation is None
    assert unavailable.route_option.missing_segments == ["ChIJ_fmKgRPnAGARkKWLtCYTu7g"]


def test_round_trip_preserves_snake_case_contract() -> None:
    # Given: fixture 를 DTO 로 역직렬화.
    parsed = TripPlanningWithRecommendationsResponse.model_validate(_payload())

    # When: 재직렬화한다.
    dumped = parsed.model_dump(mode="json")

    # Then: snake_case 필드명과 enum 문자열이 계약대로 유지된다.
    assert dumped["trip_id"] == "trip_001"
    assert dumped["status"] == "PARTIAL_SUCCESS"
    assert dumped["day_plans"][0]["route_options"][0]["travel_mode"] == "DRIVE"
    assert dumped["day_recommendations"][0]["route_options"][0]["status"] == "SUCCESS"
    # 재역직렬화도 성공(왕복 안정성).
    reparsed = TripPlanningWithRecommendationsResponse.model_validate(dumped)
    assert reparsed == parsed


def test_unknown_status_is_rejected() -> None:
    payload = _payload()
    payload["status"] = "PARTIAL"  # 폐기된 값
    with pytest.raises(ValidationError):
        TripPlanningWithRecommendationsResponse.model_validate(payload)


def test_unknown_field_is_rejected() -> None:
    payload = _payload()
    payload["surprise_field"] = 1
    with pytest.raises(ValidationError):
        TripPlanningWithRecommendationsResponse.model_validate(payload)


def test_missing_required_nested_field_is_rejected() -> None:
    payload = _payload()
    del payload["day_plans"][0]["route_options"][0]["travel_mode"]
    with pytest.raises(ValidationError):
        TripPlanningWithRecommendationsResponse.model_validate(payload)
