# 백엔드 계약 스냅샷 테스트
# 기준: backend/src/chiwawa_backend/schemas/places.py 의
#   - PhotoPlaceCandidateRead (응답 후보)
#   - PhotoPlaceSearchRequest (검색 요청)
# 백엔드를 import 하지 않고(패키지 결합 금지) 계약 필드를 스냅샷으로 고정한다.
# 어느 쪽 스키마가 바뀌면 이 테스트가 먼저 실패해 드리프트를 조기에 알린다.
import pytest
from pydantic import ValidationError

from ai.image_search.domain.schemas import PlaceCategory
from ai.image_search.domain.search_schemas import (
    CandidateSource,
    ImageSearchRequest,
    PlaceCandidate,
)

# PhotoPlaceCandidateRead 계약 필드 스냅샷 (id 는 백엔드가 next_id 로 부여하므로 제외)
BACKEND_CANDIDATE_CONTRACT: dict[str, type] = {
    "name": str,
    "city": str,
    "country": str,
    "latitude": float,
    "longitude": float,
    "confidence": float,
    "reason": str,
}

# PhotoPlaceSearchRequest 계약 필드 스냅샷 (trip.city/country 는 백엔드가 trip 에서 주입)
BACKEND_REQUEST_CONTRACT: set[str] = {"image_url", "note", "latitude", "longitude"}


# 계약 필드를 모두 채운 후보 하나를 만드는 헬퍼
def make_candidate() -> PlaceCandidate:
    return PlaceCandidate(
        name="센소지",
        city="Tokyo",
        country="Japan",
        latitude=35.7148,
        longitude=139.7967,
        confidence=0.93,
        reason="랜드마크 매치",
        category=PlaceCategory.TEMPLE_SHRINE,
        source=CandidateSource.LANDMARK,
    )


class TestCandidateContract:
    # PlaceCandidate 는 백엔드 후보 계약 필드를 전부, 올바른 타입으로 제공한다
    def test_provides_all_backend_candidate_fields(self):
        dumped = make_candidate().model_dump()

        for field, expected_type in BACKEND_CANDIDATE_CONTRACT.items():
            assert field in dumped, f"백엔드 계약 필드 누락: {field}"
            assert isinstance(dumped[field], expected_type), (
                f"{field} 타입 불일치: {type(dumped[field])} != {expected_type}"
            )

    # 계약 필드는 필수다 — 하나라도 빠지면 후보를 만들 수 없다
    def test_backend_contract_fields_are_required(self):
        base = make_candidate().model_dump()
        base.pop("place_id")  # 선택 필드 제거해도 무방

        for field in BACKEND_CANDIDATE_CONTRACT:
            broken = {k: v for k, v in base.items() if k != field}
            with pytest.raises(ValidationError):
                PlaceCandidate(**broken)

    # confidence 는 백엔드 계약(ge=0, le=1)과 같은 경계를 강제한다
    def test_confidence_matches_backend_bounds(self):
        base = make_candidate().model_dump()

        for invalid in (-0.1, 1.1):
            with pytest.raises(ValidationError):
                PlaceCandidate(**{**base, "confidence": invalid})


class TestRequestContract:
    # 백엔드 검색 요청의 모든 필드를 ImageSearchRequest 가 그대로 받을 수 있다
    def test_accepts_all_backend_request_fields(self):
        request = ImageSearchRequest(
            image_url="https://example.com/photo.jpg",
            note="야경",
            latitude=35.71,
            longitude=139.79,
        )

        for field in BACKEND_REQUEST_CONTRACT:
            assert hasattr(request, field), f"백엔드 요청 필드 누락: {field}"

    # 백엔드가 trip 에서 주입하는 city/country 힌트도 받을 수 있다
    def test_accepts_trip_context_injection(self):
        request = ImageSearchRequest(
            image_url="https://example.com/photo.jpg",
            city="Tokyo",
            country="Japan",
        )

        assert request.city == "Tokyo"
        assert request.country == "Japan"
