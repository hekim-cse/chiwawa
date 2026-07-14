# domain/schemas.py 데이터 모델의 검증 동작 테스트 (외부 API 호출 없음)
import pytest
from pydantic import ValidationError

from ai.image_search.domain.schemas import (
    CandidateSource,
    ImageSearchRequest,
    ImageSearchResult,
    LandmarkDetection,
    PlaceCandidate,
    PlaceCategory,
    RecognitionSignals,
    RecognitionStatus,
    ResolvedPlace,
    VisionIdentification,
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


class TestConfidenceBounds:
    # PlaceCandidate confidence는 0~1 범위를 벗어나면 거부한다
    def test_place_candidate_rejects_confidence_above_one(self):
        with pytest.raises(ValidationError):
            make_candidate(confidence=1.5)

    # LandmarkDetection score는 0~1 범위를 벗어나면 거부한다
    def test_landmark_detection_rejects_score_above_one(self):
        with pytest.raises(ValidationError):
            LandmarkDetection(name="에펠탑", latitude=48.8, longitude=2.29, score=2.0)

    # VisionIdentification confidence는 0~1 범위를 벗어나면 거부한다
    def test_vision_identification_rejects_negative_confidence(self):
        with pytest.raises(ValidationError):
            VisionIdentification(
                place_name_guess="어느 카페",
                category=PlaceCategory.CAFE,
                vibe_keywords=["아늑한"],
                reason="분위기 추정",
                confidence=-0.1,
            )


class TestEnums:
    # 기대하는 카테고리 값들이 존재한다
    def test_expected_categories_exist(self):
        assert PlaceCategory.LANDMARK.value == "LANDMARK"
        assert PlaceCategory.CAFE.value == "CAFE"

    # 사진 기반 검색을 위해 다양한 카테고리를 지원한다
    def test_diverse_categories_exist(self):
        expected = [
            "TEMPLE_SHRINE",
            "HISTORIC",
            "GALLERY",
            "PARK",
            "GARDEN",
            "BEACH",
            "VIEWPOINT",
            "ONSEN",
            "DESSERT",
            "BAR",
            "MARKET",
            "STREET",
            "ARCHITECTURE",
            "THEME_PARK",
            "AQUARIUM_ZOO",
        ]
        for name in expected:
            assert PlaceCategory[name].value == name

    # 인식 상태 3종이 존재한다
    def test_recognition_status_values(self):
        assert RecognitionStatus.SUCCESS.value == "SUCCESS"
        assert RecognitionStatus.PARTIAL.value == "PARTIAL"
        assert RecognitionStatus.FAILED.value == "FAILED"


class TestResolvedPlace:
    # 도시/국가/리뷰 수를 담을 수 있다 (백엔드 계약 매핑용, Places addressComponents 기반)
    def test_holds_city_country_and_review_count(self):
        place = ResolvedPlace(
            place_id="p1",
            name="센소지",
            latitude=35.7148,
            longitude=139.7967,
            city="Tokyo",
            country="Japan",
            review_count=12000,
        )

        assert place.city == "Tokyo"
        assert place.country == "Japan"
        assert place.review_count == 12000

    # 도시/국가/리뷰 수는 선택 필드다 (응답에 없을 수 있음)
    def test_city_country_review_count_default_to_none(self):
        place = ResolvedPlace(
            place_id="p1", name="센소지", latitude=35.7148, longitude=139.7967
        )

        assert place.city is None
        assert place.country is None
        assert place.review_count is None

    # 리뷰 수는 음수가 될 수 없다
    def test_rejects_negative_review_count(self):
        with pytest.raises(ValidationError):
            ResolvedPlace(
                place_id="p1",
                name="센소지",
                latitude=35.7148,
                longitude=139.7967,
                review_count=-1,
            )


class TestImageSearchResult:
    # 식별 결과와 후보 리스트를 담는다
    def test_composes_identified_and_candidates(self):
        identified = make_candidate()
        nearby = make_candidate(name="근처 카페", source=CandidateSource.NEARBY, confidence=0.6)

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
