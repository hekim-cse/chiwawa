# Modal Route Planner HTTP 호출과 외부 오류 매핑을 담당하는 Client
from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, cast

import httpx
from pydantic import ValidationError

from chiwawa_backend.errors import DomainValidationError, UpstreamServiceError
from chiwawa_backend.schemas.ai_planning import (
    TripPlanningRequest,
    TripPlanningWithRecommendationsResponse,
)

if TYPE_CHECKING:
    from chiwawa_backend.config import Settings

RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})
VALIDATION_ERROR_STATUS_CODES = frozenset({400, 422})
MAX_ERROR_DETAIL_LENGTH = 500
DEFAULT_RETRY_BACKOFF_SECONDS = 0.25
REQUEST_ERROR_MESSAGE = "경로 최적화 서비스 요청에 실패했습니다."
INVALID_RESPONSE_MESSAGE = "경로 최적화 서비스 응답 계약이 올바르지 않습니다."
UNREACHABLE_RETRY_LOOP_MESSAGE = "도달할 수 없는 경로 최적화 재시도 상태입니다."


class RemoteRoutePlanner:
    """Modal Route Planner HTTP 경계."""

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self._url: str = settings.require_route_planner_url()
        self._timeout: float = settings.route_planner_timeout_seconds
        self._max_retries: int = settings.route_planner_max_retries
        self._transport: httpx.AsyncBaseTransport | None = transport
        self._retry_backoff_seconds: float = retry_backoff_seconds

    async def plan_trip(
        self,
        request: TripPlanningRequest,
        *,
        include_recommendations: bool,
    ) -> TripPlanningWithRecommendationsResponse:
        payload = request.model_dump(mode="json", exclude_none=True)
        payload["include_recommendations"] = include_recommendations

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
                message = (
                    "경로 최적화 서비스가 일시적 오류를 반환했습니다. "
                    f"HTTP {response.status_code}"
                )
                raise UpstreamServiceError(message)
            if response.status_code in VALIDATION_ERROR_STATUS_CODES:
                raise DomainValidationError(_response_detail(response))
            if response.is_error:
                message = (
                    "경로 최적화 서비스가 오류를 반환했습니다. "
                    f"HTTP {response.status_code}"
                )
                raise UpstreamServiceError(message)

            try:
                return TripPlanningWithRecommendationsResponse.model_validate_json(
                    response.content,
                )
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
        detail_value: object
        if isinstance(payload, dict):
            payload_dict = cast("dict[str, object]", payload)
            detail_value = payload_dict.get("detail")
        else:
            detail_value = payload
        detail = (
            detail_value
            if isinstance(detail_value, str)
            else json.dumps(detail_value, ensure_ascii=False)
        )
    detail = detail.strip()
    return detail[:MAX_ERROR_DETAIL_LENGTH] or (
        f"경로 최적화 요청이 거부되었습니다. HTTP {response.status_code}"
    )
