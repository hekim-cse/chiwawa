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


def _draft_plan(trip: TripRead, plan_id: str, *, plan_date: dt.date) -> PlanDraftRead:
    stop = PlanStopRead(
        id=f"stop_of_{plan_id}",
        place_id=None,
        name="Draft stop",
        date=plan_date,
        start_time=dt.time(10),
        end_time=dt.time(11),
        notes=None,
        source=PlaceSource.PLAN,
    )
    return PlanDraftRead(
        id=plan_id,
        trip_id=trip.id,
        title="Draft",
        days=[PlanDayRead(date=plan_date, stops=[stop])],
        estimated_total_minutes=60,
    )


@pytest.mark.anyio
async def test_trip_patch_discards_unconfirmed_drafts_outside_new_range() -> None:
    # Given: 마지막 날을 참조하는 draft와 첫날만 참조하는 draft가 있는 여행.
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
    outside_plan = _draft_plan(trip, "draft_on_last_day", plan_date=trip.end_date)
    inside_plan = _draft_plan(trip, "draft_on_first_day", plan_date=trip.start_date)
    state.trips[trip.id] = trip
    state.plans[outside_plan.id] = outside_plan
    state.plans[inside_plan.id] = inside_plan
    app = create_app(state)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: 미확정 draft만 마지막 날을 참조하는 상태에서 기간을 줄인다.
        response = await client.patch(
            f"/api/v1/trips/{trip.id}",
            json={"end_date": "2026-07-11"},
        )
        outside_response = await client.get(
            f"/api/v1/trips/{trip.id}/plans/{outside_plan.id}",
        )
        inside_response = await client.get(
            f"/api/v1/trips/{trip.id}/plans/{inside_plan.id}",
        )

    # Then: 날짜 변경은 성공하고 범위를 벗어난 draft만 폐기된다.
    assert response.status_code == HTTPStatus.OK
    updated = TripRead.model_validate_json(response.text)
    assert updated.end_date.isoformat() == "2026-07-11"
    assert outside_response.status_code == HTTPStatus.NOT_FOUND
    assert inside_response.status_code == HTTPStatus.OK
