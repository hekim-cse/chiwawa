# 사진 장소 검색 API 통합 테스트용 결정적 Recognizer
from ai.image_search.domain.schemas import PlaceCategory
from ai.image_search.domain.search_schemas import (
    CandidateSource,
    ImageSearchRequest,
    ImageSearchResult,
    PlaceCandidate,
    RecognitionSignals,
    RecognitionStatus,
)
from fastapi import FastAPI

from chiwawa_backend.dependencies import get_current_user_id
from chiwawa_backend.main import create_app
from chiwawa_backend.state import AppState


class FixedPhotoPlaceRecognizer:
    def search(self, request: ImageSearchRequest) -> ImageSearchResult:
        city = request.city or "Tokyo"
        country = request.country or "Japan"
        candidate = PlaceCandidate(
            place_id="google-shibuya-sky",
            name="Shibuya Sky",
            city=city,
            country=country,
            latitude=35.6585,
            longitude=139.702,
            confidence=0.95,
            reason="fixed integration-test candidate",
            category=PlaceCategory.LANDMARK,
            source=CandidateSource.LANDMARK,
        )
        return ImageSearchResult(
            identified=candidate,
            candidates=[candidate],
            status=RecognitionStatus.SUCCESS,
            signals=RecognitionSignals(),
        )


def create_photo_place_test_app(state: AppState | None = None) -> FastAPI:
    app = create_app(
        state=state,
        photo_place_recognizer=FixedPhotoPlaceRecognizer(),
    )
    app.dependency_overrides[get_current_user_id] = lambda: 1
    return app
