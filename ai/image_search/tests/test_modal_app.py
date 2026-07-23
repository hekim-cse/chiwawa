# Modal entrypoint의 요청 검증과 PlaceRecognizer 연결(payload→JSON 직렬화) 테스트
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
from ai.image_search.modal_app import search_photo_payload


# 요청을 그대로 받아 고정된 성공 결과를 돌려주는 Fake Recognizer
class FakeRecognizer:
    def __init__(self) -> None:
        self.received_request: ImageSearchRequest | None = None

    def search(self, request: ImageSearchRequest) -> ImageSearchResult:
        self.received_request = request

        candidate = PlaceCandidate(
            name="센소지",
            city="Tokyo",
            country="Japan",
            latitude=35.7148,
            longitude=139.7967,
            confidence=0.9,
            reason="빨간 등롱과 절 문",
            category=PlaceCategory.LANDMARK,
            source=CandidateSource.LANDMARK,
            place_id="place-abc",
        )

        return ImageSearchResult(
            identified=candidate,
            candidates=[candidate],
            status=RecognitionStatus.SUCCESS,
            signals=RecognitionSignals(),
        )


# 정상 payload가 검증을 거쳐 PlaceRecognizer 결과 JSON으로 변환되는지 검증
def test_search_photo_payload_returns_json_result():
    recognizer = FakeRecognizer()

    payload = {
        "image_url": "https://example.com/photo.jpg",
        "note": "야경",
        "city": "Tokyo",
        "country": "Japan",
        "max_candidates": 5,
    }

    response_payload = search_photo_payload(
        payload=payload,
        recognizer=recognizer,
    )

    # payload가 ImageSearchRequest로 검증되어 recognizer에 전달됐는지 확인
    assert recognizer.received_request is not None
    assert (
        recognizer.received_request.image_url
        == payload["image_url"]
    )

    # 결과가 JSON 직렬화 가능한 dict로 반환되는지 확인
    assert response_payload["status"] == "SUCCESS"
    assert response_payload["identified"]["name"] == "센소지"
    assert (
        response_payload["candidates"][0]["source"]
        == "LANDMARK"
    )


# note 없이 이미지 소스만 있어도 통과하는지 검증 (선택 필드)
def test_search_photo_payload_accepts_minimal_payload():
    recognizer = FakeRecognizer()

    response_payload = search_photo_payload(
        payload={"image_url": "https://example.com/photo.jpg"},
        recognizer=recognizer,
    )

    assert response_payload["status"] == "SUCCESS"


# 이미지 소스(image_url/image_path)가 하나도 없으면 ValidationError를 발생시키는지 검증
def test_search_photo_payload_rejects_missing_image_source():
    recognizer = FakeRecognizer()

    with pytest.raises(
        ValidationError,
    ):
        search_photo_payload(
            payload={"note": "야경"},
            recognizer=recognizer,
        )

    # recognizer까지 도달하지 않고 검증 단계에서 막혔는지 확인
    assert recognizer.received_request is None
