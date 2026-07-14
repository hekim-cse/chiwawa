from __future__ import annotations

import datetime as dt
from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.base import PlaceSource, TravelStyle
from chiwawa_backend.schemas.plans import PlanDayRead, PlanDraftRead, PlanStopRead
from chiwawa_backend.schemas.schedule import ScheduleResponse
from chiwawa_backend.schemas.trips import TripRead
from chiwawa_backend.state import AppState


def _trip(trip_id: str = "trip_atomic") -> TripRead:
    return TripRead(
        id=trip_id,
        title="Atomic trip",
        city="Tokyo",
        country="Japan",
        start_date=dt.date(2026, 7, 10),
        end_date=dt.date(2026, 7, 10),
        travelers=1,
        interests=[],
        travel_style=TravelStyle.BALANCED,
    )


def _stop(stop_id: str, *, item_date: dt.date) -> PlanStopRead:
    return PlanStopRead(
        id=stop_id,
        place_id=None,
        name=stop_id,
        date=item_date,
        start_time=dt.time(9),
        end_time=dt.time(10),
        notes=None,
        source=PlaceSource.PLAN,
    )


@pytest.mark.anyio
async def test_failed_plan_confirmation_does_not_partially_mutate_schedule() -> None:
    # Given: a plan with one valid stop followed by an out-of-trip stop.
    state = AppState()
    trip = _trip()
    state.trips[trip.id] = trip
    plan = PlanDraftRead(
        id="plan_atomic",
        trip_id=trip.id,
        title="Invalid aggregate",
        days=[
            PlanDayRead(
                date=trip.start_date,
                stops=[
                    _stop("valid", item_date=trip.start_date),
                    _stop("invalid", item_date=trip.end_date + dt.timedelta(days=1)),
                ],
            ),
        ],
        estimated_total_minutes=120,
    )
    state.plans[plan.id] = plan
    app = create_app(state)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: confirmation is attempted twice.
        first = await client.post(f"/api/v1/trips/{trip.id}/plans/{plan.id}/confirm")
        second = await client.post(f"/api/v1/trips/{trip.id}/plans/{plan.id}/confirm")

    # Then: both fail without retaining or duplicating the earlier valid stop.
    assert first.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert second.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert state.schedule_items == {}
    assert plan.id not in state.confirmed_plans


@pytest.mark.anyio
async def test_replan_rejects_shift_past_trip_end_without_mutation() -> None:
    # Given: a late schedule item on the final trip day.
    state = AppState()
    trip = _trip("trip_replan_boundary")
    state.trips[trip.id] = trip
    app = create_app(state)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        item_response = await client.post(
            f"/api/v1/trips/{trip.id}/schedule-items",
            json={
                "name": "Late stop",
                "date": trip.end_date.isoformat(),
                "start_time": "23:00:00",
                "end_time": "23:30:00",
            },
        )
        assert item_response.status_code == HTTPStatus.CREATED

        # When: the delay would move the item beyond the trip boundary.
        response = await client.post(
            f"/api/v1/trips/{trip.id}/assistant/replan",
            json={"delay_minutes": 60},
        )
        schedule_response = await client.get(f"/api/v1/trips/{trip.id}/schedule")

    # Then: replanning fails before storing a plan or changing the schedule.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert len(state.plans) == 0
    schedule = ScheduleResponse.model_validate_json(schedule_response.text)
    assert len(schedule.items) == 1
