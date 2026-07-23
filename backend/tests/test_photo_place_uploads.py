from __future__ import annotations

import io
from typing import TYPE_CHECKING, cast

import pytest
from ai.image_search.domain.search_schemas import (
    CandidateSource,
    ImageSearchRequest,
    ImageSearchResult,
    PlaceCandidate,
    PlaceCategory,
    RecognitionSignals,
    RecognitionStatus,
)
from httpx import ASGITransport, AsyncClient
from PIL import Image

from chiwawa_backend.main import create_app
from chiwawa_backend.services.photo_search_uploads import (
    delete_photo_search_upload,
    save_photo_search_upload,
)

if TYPE_CHECKING:
    from pathlib import Path


class RecordingRecognizer:
    def __init__(self) -> None:
        self.requests: list[ImageSearchRequest] = []

    def search(self, request: ImageSearchRequest) -> ImageSearchResult:
        self.requests.append(request)
        candidate = PlaceCandidate(
            name="Eiffel Tower",
            city="Paris",
            country="France",
            latitude=48.8584,
            longitude=2.2945,
            confidence=0.98,
            reason="landmark test",
            category=PlaceCategory.LANDMARK,
            source=CandidateSource.LANDMARK,
        )
        return ImageSearchResult(
            identified=candidate,
            candidates=[candidate],
            status=RecognitionStatus.SUCCESS,
            signals=RecognitionSignals(),
        )


def _plain_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), "red").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.anyio
async def test_photo_place_search_relays_multipart_upload_as_temporary_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MEMORIAL_DEMO_MODE", "true")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://test.example")
    monkeypatch.setenv("PHOTO_SEARCH_UPLOAD_DIR", str(tmp_path / "uploads"))
    recognizer = RecordingRecognizer()
    app = create_app(photo_place_recognizer=recognizer)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Paris",
                "country": "France",
                "start_date": "2026-07-10",
                "end_date": "2026-07-12",
            },
        )
        trip_payload = cast("dict[str, object]", trip_response.json())
        trip_id = str(trip_payload["id"])

        response = await client.post(
            f"/api/v1/trips/{trip_id}/photo-places/search",
            files={"file": ("eiffel.png", _plain_png(), "image/png")},
            data={"note": "landmark test"},
        )

    assert response.status_code == 201
    assert len(recognizer.requests) == 1
    request = recognizer.requests[0]
    assert request.image_url is not None
    assert request.image_url.startswith(
        "https://test.example/api/v1/photo-search-images/",
    )
    assert request.note == "landmark test"
    assert not list((tmp_path / "uploads").glob("*"))


@pytest.mark.anyio
async def test_photo_place_search_keeps_json_image_url_clients_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEMORIAL_DEMO_MODE", "true")
    recognizer = RecordingRecognizer()
    app = create_app(photo_place_recognizer=recognizer)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Paris",
                "country": "France",
                "start_date": "2026-07-10",
                "end_date": "2026-07-12",
            },
        )
        trip_payload = cast("dict[str, object]", trip_response.json())
        trip_id = str(trip_payload["id"])

        response = await client.post(
            f"/api/v1/trips/{trip_id}/photo-places/search",
            json={"image_url": "https://example.com/eiffel.jpg"},
        )

    assert response.status_code == 201
    assert recognizer.requests[0].image_url == "https://example.com/eiffel.jpg"


@pytest.mark.anyio
async def test_temporary_photo_search_url_serves_the_uploaded_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PHOTO_SEARCH_UPLOAD_DIR", str(tmp_path / "uploads"))
    image = _plain_png()
    upload = save_photo_search_upload(image, tmp_path / "uploads")
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/photo-search-images/{upload.token}")

    delete_photo_search_upload(upload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == image


@pytest.mark.anyio
async def test_photo_place_search_rejects_corrupt_image_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEMORIAL_DEMO_MODE", "true")
    app = create_app(photo_place_recognizer=RecordingRecognizer())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Paris",
                "country": "France",
                "start_date": "2026-07-10",
                "end_date": "2026-07-12",
            },
        )
        trip_payload = cast("dict[str, object]", trip_response.json())
        trip_id = str(trip_payload["id"])

        response = await client.post(
            f"/api/v1/trips/{trip_id}/photo-places/search",
            files={"file": ("corrupt.png", b"not-an-image", "image/png")},
        )

    assert response.status_code == 415
