from __future__ import annotations

from http import HTTPStatus
from typing import cast

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app


@pytest.mark.anyio
async def test_trip_memorial_registers_phone_local_photo_metadata() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Tokyo",
                "country": "Japan",
                "start_date": "2026-07-10",
                "end_date": "2026-07-12",
                "travelers": 1,
                "interests": ["photos"],
                "travel_style": "balanced",
            },
        )
        trip_payload = cast("dict[str, object]", trip_response.json())
        trip_id = cast("str", trip_payload["id"])
        response = await client.post(
            f"/api/v1/trips/{trip_id}/memorial/photos",
            json={
                "device_photo_id": "device-photo-001",
                "file_name": "IMG_0001.jpg",
                "taken_at": "2026-07-10T20:30:00+09:00",
                "latitude": 35.6595,
                "longitude": 139.7005,
                "memo": "Shibuya at night",
            },
        )

    assert response.status_code == HTTPStatus.CREATED
    photo = cast("dict[str, object]", response.json())
    assert photo["device_photo_id"] == "device-photo-001"
    assert photo["storage"] == "device"
    assert "file_url" not in photo


@pytest.mark.anyio
async def test_trip_memorial_device_photo_registration_is_idempotent() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Osaka",
                "country": "Japan",
                "start_date": "2026-08-01",
                "end_date": "2026-08-03",
            },
        )
        trip_payload = cast("dict[str, object]", trip_response.json())
        trip_id = cast("str", trip_payload["id"])
        payload = {
            "device_photo_id": "device-photo-retry",
            "file_name": "IMG_0002.jpg",
            "taken_at": "2026-08-01T10:00:00+09:00",
        }

        first = await client.post(
            f"/api/v1/trips/{trip_id}/memorial/photos",
            json=payload,
        )
        second = await client.post(
            f"/api/v1/trips/{trip_id}/memorial/photos",
            json=payload,
        )
        photos = await client.get(f"/api/v1/trips/{trip_id}/memorial/photos")

    assert first.status_code == HTTPStatus.CREATED
    assert second.status_code == HTTPStatus.CREATED
    assert second.json()["id"] == first.json()["id"]
    photo_payload = cast("dict[str, object]", photos.json())
    items = cast("list[object]", photo_payload["items"])
    assert len(items) == 1


@pytest.mark.anyio
async def test_generate_memorial_sorts_photo_fallback_timeline_by_taken_at() -> None:
    # Given: 스케줄이 없는 여행에 저녁 사진을 먼저, 아침 사진을 나중에,
    #        촬영 시각이 없는 사진을 마지막에 등록한 상황.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Kyoto",
                "country": "Japan",
                "start_date": "2026-08-01",
                "end_date": "2026-08-02",
            },
        )
        trip_payload = cast("dict[str, object]", trip_response.json())
        trip_id = cast("str", trip_payload["id"])
        uploads = [
            {"file_name": "evening.jpg", "taken_at": "2026-08-01T18:00:00+09:00"},
            {"file_name": "morning.jpg", "taken_at": "2026-08-01T09:00:00+09:00"},
            {"file_name": "no-time.jpg"},
        ]
        for payload in uploads:
            upload_response = await client.post(
                f"/api/v1/trips/{trip_id}/memorial/photos",
                json=payload,
            )
            assert upload_response.status_code == HTTPStatus.CREATED

        # When: 추억 타임라인을 생성한다.
        generate_response = await client.post(
            f"/api/v1/trips/{trip_id}/memorial/generate",
            json={},
        )

    # Then: 업로드 순서가 아니라 촬영 시각 순서여야 하고,
    #       촬영 시각이 없는 사진은 0001년 placeholder 없이 맨 뒤에 와야 한다.
    assert generate_response.status_code == HTTPStatus.CREATED
    memorial = cast("dict[str, object]", generate_response.json())
    assert memorial["timeline"] == [
        "2026-08-01T09:00:00+09:00 morning.jpg",
        "2026-08-01T18:00:00+09:00 evening.jpg",
        "no-time.jpg",
    ]
