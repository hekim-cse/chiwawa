# Google Time Zone API를 이용한 전 세계 여행 시간대 Provider
from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from chiwawa_backend.errors import UpstreamServiceError

if TYPE_CHECKING:
    from chiwawa_backend.config import Settings

GOOGLE_TIME_ZONE_URL = "https://maps.googleapis.com/maps/api/timezone/json"
TIME_ZONE_REQUEST_ERROR = "Google 시간대 조회 요청에 실패했습니다."
TIME_ZONE_RESPONSE_ERROR = "Google 시간대 조회 응답 계약이 올바르지 않습니다."
TIME_ZONE_REQUEST_DENIED_ERROR = (
    "Google Time Zone API 요청이 거부됐습니다. API 활성화와 키 제한을 확인해 주세요."
)
TIME_ZONE_ZERO_RESULTS_ERROR = "출발지 좌표에 해당하는 시간대를 찾지 못했습니다."


class GoogleTimeZoneProvider:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key: str = settings.require_google_maps_api_key()
        self._timeout: float = settings.time_zone_timeout_seconds
        self._transport: httpx.AsyncBaseTransport | None = transport

    async def resolve(
        self,
        *,
        latitude: float,
        longitude: float,
        date: dt.date,
    ) -> str:
        timestamp = int(
            dt.datetime.combine(
                date,
                dt.time(hour=12),
                tzinfo=dt.UTC,
            ).timestamp(),
        )
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.get(
                    GOOGLE_TIME_ZONE_URL,
                    params={
                        "location": f"{latitude},{longitude}",
                        "timestamp": timestamp,
                        "key": self._api_key,
                        "language": "ko",
                    },
                )
        except httpx.RequestError as error:
            raise UpstreamServiceError(TIME_ZONE_REQUEST_ERROR) from error
        if response.is_error:
            message = f"Google 시간대 서비스 오류: HTTP {response.status_code}"
            raise UpstreamServiceError(message)
        try:
            payload = cast("object", response.json())
        except ValueError as error:
            raise UpstreamServiceError(TIME_ZONE_RESPONSE_ERROR) from error
        if not isinstance(payload, dict):
            raise UpstreamServiceError(TIME_ZONE_RESPONSE_ERROR)
        data = cast("dict[str, object]", payload)
        google_status = data.get("status")
        if google_status == "REQUEST_DENIED":
            raise UpstreamServiceError(TIME_ZONE_REQUEST_DENIED_ERROR)
        if google_status == "ZERO_RESULTS":
            raise UpstreamServiceError(TIME_ZONE_ZERO_RESULTS_ERROR)
        if google_status != "OK" or not isinstance(
            data.get("timeZoneId"),
            str,
        ):
            raise UpstreamServiceError(TIME_ZONE_RESPONSE_ERROR)
        timezone = cast("str", data["timeZoneId"])
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as error:
            raise UpstreamServiceError(TIME_ZONE_RESPONSE_ERROR) from error
        return timezone
