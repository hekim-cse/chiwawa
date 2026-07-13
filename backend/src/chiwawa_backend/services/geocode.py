"""Google Geocoding API 역지오코딩 (위경도 → 주소 문자열).

GOOGLE_MAPS_API_KEY 환경변수가 없거나 호출에 실패하면 None을 반환하고,
사진 업로드 자체는 계속 진행된다.
"""

from __future__ import annotations

import os
from typing import cast

import httpx

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def reverse_geocode(latitude: float, longitude: float) -> str | None:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return None
    try:
        response = httpx.get(
            GEOCODE_URL,
            params={
                "latlng": f"{latitude},{longitude}",
                "key": api_key,
                "language": "ko",
            },
            timeout=5.0,
        )
        _ = response.raise_for_status()
        payload = cast("object", response.json())
    except httpx.HTTPError:
        return None
    return _first_formatted_address(payload)


def _first_formatted_address(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    results = cast("dict[str, object]", payload).get("results")
    if not isinstance(results, list) or not results:
        return None
    first = cast("list[object]", results)[0]
    if not isinstance(first, dict):
        return None
    address = cast("dict[str, object]", first).get("formatted_address")
    return address if isinstance(address, str) else None
