from __future__ import annotations

from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.schedule import ScheduleItemRead
from chiwawa_backend.schemas.trips import TripRead


async def _create_trip(
    client: AsyncClient,
    *,
    start_date: str = "2026-07-10",
    end_date: str = "2026-07-12",
) -> TripRead:
    response = await client.post(
        "/api/v1/trips",
        json={
            "city": "Tokyo",
            "country": "Japan",
            "start_date": start_date,
            "end_date": end_date,
            "travelers": 1,
            "interests": ["food"],
            "travel_style": "balanced",
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    return TripRead.model_validate_json(response.text)


async def _create_schedule_item(
    client: AsyncClient,
    trip_id: str,
    *,
    name: str,
    start_time: str,
    end_time: str,
) -> ScheduleItemRead:
    response = await client.post(
        f"/api/v1/trips/{trip_id}/schedule-items",
        json={
            "name": name,
            "date": "2026-07-10",
            "start_time": start_time,
            "end_time": end_time,
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    return ScheduleItemRead.model_validate_json(response.text)


@pytest.mark.anyio
async def test_schedule_rejects_reversed_time_window() -> None:
    # Given: a trip and a schedule item whose end precedes its start.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)

        # When: the invalid item is submitted.
        response = await client.post(
            f"/api/v1/trips/{trip.id}/schedule-items",
            json={
                "name": "Impossible stop",
                "date": "2026-07-10",
                "start_time": "11:00:00",
                "end_time": "10:00:00",
            },
        )

    # Then: schema validation rejects it.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_schedule_rejects_date_outside_trip() -> None:
    # Given: a trip ending on July 12.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)

        # When: an otherwise valid schedule item targets July 13.
        response = await client.post(
            f"/api/v1/trips/{trip.id}/schedule-items",
            json={
                "name": "Outside trip",
                "date": "2026-07-13",
                "start_time": "10:00:00",
                "end_time": "11:00:00",
            },
        )

    # Then: the domain boundary returns a validation response.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == "schedule date must be within trip dates"


@pytest.mark.anyio
async def test_schedule_patch_validates_combined_time_window() -> None:
    # Given: a valid persisted schedule item.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)
        item = await _create_schedule_item(
            client,
            trip.id,
            name="Morning stop",
            start_time="09:00:00",
            end_time="10:00:00",
        )

        # When: a partial patch moves only the start beyond the existing end.
        response = await client.patch(
            f"/api/v1/trips/{trip.id}/schedule-items/{item.id}",
            json={"start_time": "11:00:00"},
        )

    # Then: validation evaluates the merged item, not just the partial payload.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == "end_time must be after start_time"


@pytest.mark.anyio
async def test_trip_patch_rejects_reversed_dates() -> None:
    # Given: a valid trip date range.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)

        # When: a partial patch moves the start beyond the existing end.
        response = await client.patch(
            f"/api/v1/trips/{trip.id}",
            json={"start_date": "2026-07-13"},
        )

    # Then: the backend rejects the invalid resulting aggregate.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == "end_date must not be before start_date"


@pytest.mark.anyio
async def test_free_time_rejects_reversed_time_window() -> None:
    # Given: a trip and a reversed recommendation window.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)

        # When: the recommendation request is submitted.
        response = await client.post(
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations",
            json={
                "date": "2026-07-10",
                "start_time": "17:00:00",
                "end_time": "15:00:00",
            },
        )

    # Then: the request boundary rejects it.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
