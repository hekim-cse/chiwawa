from __future__ import annotations

import httpx
import pytest
from ai.image_search.domain.search_schemas import ImageSearchRequest

from chiwawa_backend.config import Settings
from chiwawa_backend.errors import DomainValidationError, UpstreamServiceError
from chiwawa_backend.services.image_search_client import (
    RemotePhotoPlaceRecognizer,
)


def _settings() -> Settings:
    return Settings(
        image_search_url="https://modal.example/search_photo",
        image_search_max_retries=1,
    )


def _success_payload() -> dict[str, object]:
    candidate = {
        "name": "Senso-ji",
        "city": "Tokyo",
        "country": "Japan",
        "latitude": 35.7148,
        "longitude": 139.7967,
        "confidence": 0.93,
        "reason": "Visible temple gate",
        "category": "TEMPLE_SHRINE",
        "source": "LANDMARK",
    }
    return {
        "identified": candidate,
        "candidates": [candidate],
        "status": "SUCCESS",
        "signals": {"landmark": None, "llm": None},
    }


def _request() -> ImageSearchRequest:
    return ImageSearchRequest(
        image_url="https://images.example/photo.jpg",
        note="night temple photo",
        latitude=35.71,
        longitude=139.79,
        city="Tokyo",
        country="Japan",
        max_candidates=5,
    )


@pytest.mark.anyio
async def test_remote_search_posts_contract_and_parses_result() -> None:
    received_body = b""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal received_body
        received_body = request.content
        return httpx.Response(200, json=_success_payload())

    recognizer = RemotePhotoPlaceRecognizer(
        _settings(),
        transport=httpx.MockTransport(handler),
        retry_backoff_seconds=0,
    )

    result = await recognizer.search(_request())

    assert result.candidates[0].name == "Senso-ji"
    assert b"images.example/photo.jpg" in received_body
    assert b"night temple photo" in received_body


@pytest.mark.anyio
async def test_remote_422_becomes_domain_validation_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(422, json={"detail": "image download failed"})

    recognizer = RemotePhotoPlaceRecognizer(
        _settings(),
        transport=httpx.MockTransport(handler),
        retry_backoff_seconds=0,
    )

    with pytest.raises(DomainValidationError, match="image download failed"):
        _ = await recognizer.search(_request())


@pytest.mark.anyio
async def test_remote_retries_transient_status_once() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        _ = request
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"detail": "warming up"})
        return httpx.Response(200, json=_success_payload())

    recognizer = RemotePhotoPlaceRecognizer(
        _settings(),
        transport=httpx.MockTransport(handler),
        retry_backoff_seconds=0,
    )

    result = await recognizer.search(_request())

    assert attempts == 2
    assert result.status.name == "SUCCESS"


@pytest.mark.anyio
async def test_remote_timeout_after_retry_becomes_upstream_error() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        _ = request
        attempts += 1
        message = "modal timeout"
        raise httpx.ReadTimeout(message)

    recognizer = RemotePhotoPlaceRecognizer(
        _settings(),
        transport=httpx.MockTransport(handler),
        retry_backoff_seconds=0,
    )

    with pytest.raises(UpstreamServiceError, match="image search service"):
        _ = await recognizer.search(_request())

    assert attempts == 2
