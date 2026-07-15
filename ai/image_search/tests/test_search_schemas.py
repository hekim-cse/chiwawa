# domain/search_schemas.py (백엔드 계약 DTO) 검증 테스트 (외부 API 호출 없음)
import pytest
from pydantic import ValidationError

from ai.image_search.domain.schemas import PlaceCategory
from ai.image_search.domain.search_schemas import (
    CandidateSource,
    ImageSearchRequest,
    ImageSearchResult,
    PlaceCandidate,
    RecognitionSignals,
    RecognitionStatus,
)


# 후보 하나 만드는 헬퍼 (테스트 반복 축소)
def make_candidate(**overrides) -> PlaceCandidate:
    defaults = dict(
        name="센소지",
        city="Tokyo",
        country="Japan",
        latitude=35.7148,
        longitude=139.7967,
        confidence=0.9,
        reason="랜드마크 매치",
        category=PlaceCategory.LANDMARK,
        source=CandidateSource.LANDMARK,
    )
    defaults.update(overrides)
    return PlaceCandidate(**defaults)


class TestImageSearchRequest:
    # image_url만 있어도 유효하고, 기본값이 채워진다
    def test_accepts_image_url_only(self):
        req = ImageSearchRequest(image_url="https://example.com/a.jpg")

        assert req.image_url == "https://example.com/a.jpg"
        assert req.image_path is None
        assert req.max_candidates == 5

    # image_path만 있어도 유효하다
    def test_accepts_image_path_only(self):
        req = ImageSearchRequest(image_path="/tmp/photo.jpg")

        assert req.image_path == "/tmp/photo.jpg"

    # image_url도 image_path도 없으면 거부한다 (model_validator)
    def test_requires_at_least_one_image_source(self):
        with pytest.raises(ValidationError):
            ImageSearchRequest(note="야경")

    # 위도 범위를 벗어나면 거부한다
    def test_rejects_out_of_range_latitude(self):
        with pytest.raises(ValidationError):
            ImageSearchRequest(image_url="https://x/y.jpg", latitude=91.0)

    # 경도 범위를 벗어나면 거부한다
    def test_rejects_out_of_range_longitude(self):
        with pytest.raises(ValidationError):
            ImageSearchRequest(image_url="https://x/y.jpg", longitude=181.0)

    # max_candidates는 1 이상이어야 한다
    def test_rejects_non_positive_max_candidates(self):
        with pytest.raises(ValidationError):
            ImageSearchRequest(image_url="https://x/y.jpg", max_candidates=0)


class TestPlaceCandidate:
    # confidence 는 0~1 범위를 벗어나면 거부한다 (백엔드 계약과 동일 경계)
    def test_rejects_confidence_above_one(self):
        with pytest.raises(ValidationError):
            make_candidate(confidence=1.5)


class TestRecognitionStatus:
    # 인식 상태 3종이 존재한다
    def test_recognition_status_values(self):
        assert RecognitionStatus.SUCCESS.value == "SUCCESS"
        assert RecognitionStatus.PARTIAL.value == "PARTIAL"
        assert RecognitionStatus.FAILED.value == "FAILED"


class TestImageSearchResult:
    # 식별 결과와 후보 리스트를 담는다
    def test_composes_identified_and_candidates(self):
        identified = make_candidate()
        nearby = make_candidate(
            name="근처 카페", source=CandidateSource.NEARBY, confidence=0.6
        )

        result = ImageSearchResult(
            identified=identified,
            candidates=[identified, nearby],
            status=RecognitionStatus.SUCCESS,
            signals=RecognitionSignals(landmark=None, llm=None),
        )

        assert result.identified.name == "센소지"
        assert len(result.candidates) == 2
        assert result.candidates[1].source is CandidateSource.NEARBY
        assert result.status is RecognitionStatus.SUCCESS

    # 식별 실패 시 identified=None, 빈 후보, FAILED 를 표현할 수 있다
    def test_can_represent_failed_result(self):
        result = ImageSearchResult(
            identified=None,
            candidates=[],
            status=RecognitionStatus.FAILED,
            signals=RecognitionSignals(landmark=None, llm=None),
        )

        assert result.identified is None
        assert result.candidates == []
        assert result.status is RecognitionStatus.FAILED
