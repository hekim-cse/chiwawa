# Modal 통합 일정 최적화·추천 외부 응답 계약 테스트
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai.free_time_recommender.adapters.modal_response import (
    TripPlanningWithRecommendationsResponseDTO,
)
from ai.route_planner.scripts.export_modal_response_schema import (
    OUTPUT_PATH,
    build_schema,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "route_planner"
    / "tests"
    / "fixtures"
    / "trip_planning_with_recommendations_response.json"
)


def load_fixture() -> dict[str, object]:
    """Backend와 공유할 대표 통합 응답 Fixture를 읽는다."""

    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_representative_fixture_round_trips_without_contract_loss() -> None:
    """대표 Fixture가 DTO 재직렬화에서 동일하게 유지된다."""

    payload = load_fixture()
    response = TripPlanningWithRecommendationsResponseDTO.model_validate(
        payload
    )

    assert response.status.value == "PARTIAL_SUCCESS"
    assert response.model_dump(mode="json") == payload


def test_contract_rejects_legacy_partial_status() -> None:
    """기존 PARTIAL 문자열을 통합 계약에서 허용하지 않는다."""

    payload = load_fixture()
    payload["status"] = "PARTIAL"

    with pytest.raises(ValidationError):
        TripPlanningWithRecommendationsResponseDTO.model_validate(payload)


@pytest.mark.parametrize(
    ("status", "recommendation"),
    [
        ("SUCCESS", None),
        (
            "UNAVAILABLE",
            {
                "route_leg_geometries": [],
                "recommendation_groups": [],
            },
        ),
    ],
)
def test_contract_rejects_inconsistent_recommendation_status(
    status: str,
    recommendation: dict[str, object] | None,
) -> None:
    """추천 상태와 nullable recommendation 조합을 엄격히 검증한다."""

    payload = load_fixture()
    outcome = payload["day_recommendations"][0]["route_options"][0]
    outcome["status"] = status
    outcome["recommendation"] = recommendation

    with pytest.raises(ValidationError):
        TripPlanningWithRecommendationsResponseDTO.model_validate(payload)


def test_checked_in_json_schema_matches_response_dto() -> None:
    """DTO와 체크인된 Schema가 일치해야 한다."""

    checked_in_schema = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert checked_in_schema == build_schema()
