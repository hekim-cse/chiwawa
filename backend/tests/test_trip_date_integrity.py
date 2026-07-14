from __future__ import annotations

import datetime as dt
from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.base import PlaceSource, TravelStyle
from chiwawa_backend.schemas.plans import PlanDayRead, PlanDraftRead, PlanStopRead
from chiwawa_backend.schemas.trips import TripRead
from chiwawa_backend.state import AppState


@pytest.mark.anyio
async def test_trip_patch_keeps_existing_recommendations_in_range() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Tokyo",
                "start_date": "2026-07-10",
                "end_date": "2026-07-12",
            },
        )
        trip = TripRead.model_validate_json(trip_response.text)
        recommendation_response = await client.post(
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations",
            json={
                "date": "2026-07-12",
                "start_time": "15:00:00",
                "end_time": "16:00:00",
            },
        )
        assert recommendation_response.status_code == HTTPStatus.CREATED

        patch_response = await client.patch(
            f"/api/v1/trips/{trip.id}",
            json={"end_date": "2026-07-11"},
        )
        read_response = await client.get(f"/api/v1/trips/{trip.id}")

    assert patch_response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    persisted = TripRead.model_validate_json(read_response.text)
    assert persisted.end_date.isoformat() == "2026-07-12"


@pytest.mark.anyio
async def test_trip_patch_keeps_unconfirmed_plan_dates_in_range() -> None:
    state = AppState()
    trip = TripRead(
        id="trip_with_draft",
        title="Tokyo travel",
        city="Tokyo",
        country="Japan",
        start_date=dt.date(2026, 7, 10),
        end_date=dt.date(2026, 7, 12),
        travelers=1,
        interests=[],
        travel_style=TravelStyle.BALANCED,
    )
    stop = PlanStopRead(
        id="stop_on_last_day",
        place_id=None,
        name="Last-day stop",
        date=trip.end_date,
        start_time=dt.time(10),
        end_time=dt.time(11),
        notes=None,
        source=PlaceSource.PLAN,
    )
    plan = PlanDraftRead(
        id="unconfirmed_plan",
        trip_id=trip.id,
        title="Draft",
        days=[PlanDayRead(date=trip.end_date, stops=[stop])],
        estimated_total_minutes=60,
    )
    state.trips[trip.id] = trip
    state.plans[plan.id] = plan
    app = create_app(state)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.patch(
            f"/api/v1/trips/{trip.id}",
            json={"end_date": "2026-07-11"},
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
