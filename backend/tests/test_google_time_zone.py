# Google Time Zone Provider의 전 세계 좌표 변환 계약 테스트
from __future__ import annotations

import datetime as dt
import json

import httpx
import pytest
from pydantic import SecretStr

from chiwawa_backend.config import Settings
from chiwawa_backend.errors import UpstreamServiceError
from chiwawa_backend.services.google_time_zone import GoogleTimeZoneProvider


def _settings() -> Settings:
    return Settings(
        google_maps_api_key=SecretStr("test-key"),
        _env_file=None,
    )


@pytest.mark.anyio
async def test_resolve_returns_valid_iana_timezone_for_coordinate() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={"status": "OK", "timeZoneId": "America/New_York"},
        )

    provider = GoogleTimeZoneProvider(
        _settings(),
        transport=httpx.MockTransport(handler),
    )
    result = await provider.resolve(
        latitude=40.7128,
        longitude=-74.006,
        date=dt.date(2026, 8, 1),
    )

    assert result == "America/New_York"
    assert captured["location"] == "40.7128,-74.006"
    assert captured["key"] == "test-key"


@pytest.mark.anyio
async def test_resolve_maps_invalid_google_contract_to_explicit_error() -> None:
    provider = GoogleTimeZoneProvider(
        _settings(),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=json.dumps({"status": "REQUEST_DENIED"}).encode(),
            ),
        ),
    )

    with pytest.raises(UpstreamServiceError, match="API 활성화와 키 제한"):
        await provider.resolve(
            latitude=48.8566,
            longitude=2.3522,
            date=dt.date(2026, 8, 1),
        )
