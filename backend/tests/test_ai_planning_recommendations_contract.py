# Modal 통합 응답(일정 최적화 + 추천) 계약 검증 테스트
#   AI가 제공하는 정본 fixture를 백엔드에서도 그대로 사용해(단일 원천)
#   타입/enum/nullable 계약이 양쪽에서 동일한지 검증한다.
#   cd backend && uv run pytest tests/test_ai_planning_recommendations_contract.py

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from chiwawa_backend.schemas.ai_planning import (
    RecommendationCategory,
    RecommendationStatus,
    RouteInsertionRejectionReason,
    TripPlanningStatus,
    TripPlanningWithRecommendationsResponse,
)

# AI Route Planner 가 백엔드와 공유하려고 만든 정본 통합 응답 fixture.
AI_CANONICAL_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "ai"
    / "route_planner"
    / "tests"
    / "fixtures"
    / "trip_planning_with_recommendations_response.json"
)


def _payload() -> dict[str, object]:
    return json.loads(AI_CANONICAL_FIXTURE.read_text(encoding="utf-8"))


def test_backend_dto_parses_ai_canonical_fixture() -> None:
    # Given/When: AI 정본 fixture 를 백엔드 통합 응답 DTO 로 파싱.
    parsed = TripPlanningWithRecommendationsResponse.model_validate(_payload())

    # Then: 최상위 + day_plans.route_options 구조가 파싱된다.
    assert parsed.status is TripPlanningStatus.PARTIAL_SUCCESS
    day = parsed.day_plans[0]
    assert day.route_options[0].travel_mode == "DRIVE"


def test_recommendation_types_match_ai_contract() -> None:
    parsed = TripPlanningWithRecommendationsResponse.model_validate(_payload())
    day_rec = parsed.day_recommendations[0]

    success = day_rec.route_options[0]
    assert success.status is RecommendationStatus.SUCCESS
    assert success.recommendation is not None

    group = success.recommendation.recommendation_groups[0]
    # category 는 str 이 아니라 enum 이어야 한다.
    assert isinstance(group.category, RecommendationCategory)

    candidate = group.recommendations[0]
    assert isinstance(candidate.candidate.category, RecommendationCategory)
    # 추천 시각 필드는 datetime 으로 파싱되어야 한다.
    assert isinstance(candidate.window.previous_departure_at, dt.datetime)
    assert isinstance(candidate.route_metrics.candidate_arrival_at, dt.datetime)
    assert isinstance(candidate.insertion_impact.updated_next_arrival_at, dt.datetime)
    # rejection_reasons 는 enum 리스트 타입이어야 한다.
    assert all(
        isinstance(reason, RouteInsertionRejectionReason)
        for reason in candidate.insertion_impact.rejection_reasons
    )

    # route_leg_geometries 는 dict 가 아니라 타입이 정의된 DTO 여야 한다.
    geometry = success.recommendation.route_leg_geometries[0]
    assert geometry.day_index == 1
    assert geometry.geometry.encoded_polyline

    # UNAVAILABLE 은 recommendation 이 null 이고 원본 route_option 은 유지된다.
    unavailable = day_rec.route_options[1]
    assert unavailable.status is RecommendationStatus.UNAVAILABLE
    assert unavailable.recommendation is None


def test_round_trip_is_stable() -> None:
    parsed = TripPlanningWithRecommendationsResponse.model_validate(_payload())
    dumped = parsed.model_dump(mode="json")
    assert dumped["status"] == "PARTIAL_SUCCESS"
    reparsed = TripPlanningWithRecommendationsResponse.model_validate(dumped)
    assert reparsed == parsed


def test_unknown_status_is_rejected() -> None:
    payload = _payload()
    payload["status"] = "PARTIAL"  # 폐기된 값
    with pytest.raises(ValidationError):
        TripPlanningWithRecommendationsResponse.model_validate(payload)


def test_unknown_category_is_rejected() -> None:
    payload = _payload()
    groups = payload["day_recommendations"][0]["route_options"][0]["recommendation"][
        "recommendation_groups"
    ]
    groups[0]["category"] = "NOT_A_CATEGORY"
    with pytest.raises(ValidationError):
        TripPlanningWithRecommendationsResponse.model_validate(payload)


def test_unknown_rejection_reason_is_rejected() -> None:
    payload = _payload()
    impact = payload["day_recommendations"][0]["route_options"][0]["recommendation"][
        "recommendation_groups"
    ][0]["recommendations"][0]["insertion_impact"]
    impact["rejection_reasons"] = ["NOT_A_REASON"]
    with pytest.raises(ValidationError):
        TripPlanningWithRecommendationsResponse.model_validate(payload)


def test_unknown_field_is_rejected() -> None:
    payload = _payload()
    payload["surprise_field"] = 1
    with pytest.raises(ValidationError):
        TripPlanningWithRecommendationsResponse.model_validate(payload)
