# domain/schemas.py (내부/provider 모델) 검증 테스트 (외부 API 호출 없음)
import pytest
from pydantic import ValidationError

from ai.image_search.domain.schemas import (
    LandmarkDetection,
    PlaceCategory,
    ResolvedPlace,
    VisionIdentification,
)


class TestPlaceCategory:
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


class TestLandmarkDetection:
    # score 는 0~1 범위를 벗어나면 거부한다
    def test_rejects_score_above_one(self):
        with pytest.raises(ValidationError):
            LandmarkDetection(name="에펠탑", latitude=48.8, longitude=2.29, score=2.0)


class TestVisionIdentification:
    # confidence 는 0~1 범위를 벗어나면 거부한다
    def test_rejects_negative_confidence(self):
        with pytest.raises(ValidationError):
            VisionIdentification(
                place_name_guess="어느 카페",
                category=PlaceCategory.CAFE,
                vibe_keywords=["아늑한"],
                reason="분위기 추정",
                confidence=-0.1,
            )


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

    # Google 장소 유형(primaryType)을 담을 수 있고, 없으면 None 이다
    def test_holds_optional_primary_type(self):
        with_type = ResolvedPlace(
            place_id="p1", name="카페", latitude=0, longitude=0, primary_type="cafe"
        )
        without_type = ResolvedPlace(
            place_id="p2", name="어딘가", latitude=0, longitude=0
        )

        assert with_type.primary_type == "cafe"
        assert without_type.primary_type is None

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
