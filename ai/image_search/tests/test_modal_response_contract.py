# Modal 이미지 검색 외부 응답 계약 테스트
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai.image_search.domain.search_schemas import ImageSearchResult
from ai.image_search.scripts.export_modal_response_schema import (
    OUTPUT_PATH,
    build_schema,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "image_search_response.json"
)


def load_fixture() -> dict[str, object]:
    """Backend와 공유할 대표 이미지 검색 응답 Fixture를 읽는다."""

    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_representative_fixture_round_trips_without_contract_loss() -> None:
    """대표 Fixture가 DTO 재직렬화에서 동일하게 유지된다."""

    payload = load_fixture()
    response = ImageSearchResult.model_validate(payload)

    assert response.status.value == "SUCCESS"
    assert response.identified is not None
    assert response.model_dump(mode="json") == payload


def test_contract_rejects_out_of_range_confidence() -> None:
    """confidence 범위를 벗어난 후보를 계약이 거부한다."""

    payload = load_fixture()
    payload["candidates"][0]["confidence"] = 1.5

    with pytest.raises(ValidationError):
        ImageSearchResult.model_validate(payload)


def test_contract_rejects_unknown_recognition_status() -> None:
    """폐집합 밖의 status 문자열을 계약이 거부한다."""

    payload = load_fixture()
    payload["status"] = "DONE"

    with pytest.raises(ValidationError):
        ImageSearchResult.model_validate(payload)


def test_checked_in_json_schema_matches_response_dto() -> None:
    """DTO와 체크인된 Schema가 일치해야 한다."""

    checked_in_schema = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert checked_in_schema == build_schema()
