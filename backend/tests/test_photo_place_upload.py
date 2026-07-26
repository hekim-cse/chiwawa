# 브라우저 이미지 업로드와 AI 사진 분석 계약 통합 테스트
from __future__ import annotations

import base64
from http import HTTPStatus

import pytest
from ai.image_search.domain.search_schemas import (
    ImageSearchRequest,
    ImageSearchResult,
    RecognitionSignals,
    RecognitionStatus,
)
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.dependencies import get_current_user_id
from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.trips import TripRead


class CapturingRecognizer:
    def __init__(self) -> None:
        self.request: ImageSearchRequest | None = None

    def search(self, request: ImageSearchRequest) -> ImageSearchResult:
        self.request = request
        return ImageSearchResult(
            identified=None,
            candidates=[],
            status=RecognitionStatus.FAILED,
            signals=RecognitionSignals(),
        )


@pytest.mark.anyio
async def test_photo_upload_reaches_recognizer_as_base64() -> None:
    recognizer = CapturingRecognizer()
    app = create_app(photo_place_recognizer=recognizer)
    app.dependency_overrides[get_current_user_id] = lambda: 1

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Paris",
                "country": "France",
                "start_date": "2026-08-01",
                "end_date": "2026-08-01",
            },
        )
        trip_id = TripRead.model_validate(trip_response.json()).id
        image_bytes = b"\x89PNG\r\n\x1a\nphoto"

        response = await client.post(
            f"/api/v1/trips/{trip_id}/photo-places/search-upload",
            files={"file": ("eiffel.png", image_bytes, "image/png")},
        )

    assert response.status_code == HTTPStatus.CREATED
    assert recognizer.request is not None
    assert recognizer.request.image_mime_type == "image/png"
    assert base64.b64decode(recognizer.request.image_base64 or "") == image_bytes


@pytest.mark.anyio
async def test_photo_upload_rejects_non_image_file() -> None:
    recognizer = CapturingRecognizer()
    app = create_app(photo_place_recognizer=recognizer)
    app.dependency_overrides[get_current_user_id] = lambda: 1

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Paris",
                "country": "France",
                "start_date": "2026-08-01",
                "end_date": "2026-08-01",
            },
        )
        trip_id = TripRead.model_validate(trip_response.json()).id
        response = await client.post(
            f"/api/v1/trips/{trip_id}/photo-places/search-upload",
            files={"file": ("note.txt", b"not-image", "text/plain")},
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert recognizer.request is None
