from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, cast

import httpx
from ai.image_search.domain.search_schemas import ImageSearchRequest, ImageSearchResult
from pydantic import ValidationError

from chiwawa_backend.errors import DomainValidationError, UpstreamServiceError

if TYPE_CHECKING:
    from pydantic import BaseModel

    from chiwawa_backend.config import Settings

RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})
VALIDATION_ERROR_STATUS_CODES = frozenset({400, 422})
HTTP_ERROR_STATUS_CODE = 400
DEFAULT_RETRY_BACKOFF_SECONDS = 0.25
MAX_ERROR_DETAIL_LENGTH = 500
REQUEST_ERROR_MESSAGE = "image search service request failed"
INVALID_RESPONSE_MESSAGE = "image search service returned an invalid response"
UNREACHABLE_RETRY_LOOP_MESSAGE = "unreachable retry loop"


class RemotePhotoPlaceRecognizer:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self._url: str = settings.require_image_search_url()
        self._timeout: float = settings.image_search_timeout_seconds
        self._max_retries: int = settings.image_search_max_retries
        self._transport: httpx.AsyncBaseTransport | None = transport
        self._retry_backoff_seconds: float = retry_backoff_seconds

    async def search(self, request: ImageSearchRequest) -> ImageSearchResult:
        payload = cast(
            "dict[str, object]",
            cast("BaseModel", cast("object", request)).model_dump(
                mode="json",
                exclude_none=True,
            ),
        )
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout,
                    transport=self._transport,
                ) as client:
                    response = await client.post(self._url, json=payload)
            except httpx.RequestError as error:
                if attempt < self._max_retries:
                    await self._wait_before_retry(attempt)
                    continue
                raise UpstreamServiceError(REQUEST_ERROR_MESSAGE) from error

            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt < self._max_retries:
                    await self._wait_before_retry(attempt)
                    continue
                message = f"image search service returned HTTP {response.status_code}"
                raise UpstreamServiceError(message)
            if response.status_code in VALIDATION_ERROR_STATUS_CODES:
                raise DomainValidationError(_response_detail(response))
            if response.status_code >= HTTP_ERROR_STATUS_CODE:
                message = f"image search service returned HTTP {response.status_code}"
                raise UpstreamServiceError(message)

            try:
                result = cast("type[BaseModel]", ImageSearchResult).model_validate_json(
                    response.content,
                )
                return cast("ImageSearchResult", cast("object", result))
            except (ValidationError, ValueError) as error:
                raise UpstreamServiceError(INVALID_RESPONSE_MESSAGE) from error

        raise AssertionError(UNREACHABLE_RETRY_LOOP_MESSAGE)

    async def _wait_before_retry(self, attempt: int) -> None:
        delay = self._retry_backoff_seconds * (attempt + 1)
        if delay > 0:
            await asyncio.sleep(delay)


def _response_detail(response: httpx.Response) -> str:
    try:
        payload = cast("object", response.json())
    except ValueError:
        detail = response.text
    else:
        if isinstance(payload, dict):
            payload_dict = cast("dict[str, object]", payload)
            detail_value: object = payload_dict.get("detail")
        else:
            detail_value = payload
        detail = (
            detail_value
            if isinstance(detail_value, str)
            else json.dumps(detail_value, ensure_ascii=False)
        )
    detail = detail.strip()
    return detail[:MAX_ERROR_DETAIL_LENGTH] or (
        f"image search service returned HTTP {response.status_code}"
    )
