from __future__ import annotations

import datetime as dt
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.base import PlaceSource, TravelStyle
from chiwawa_backend.schemas.places import (
    ConfirmedPhotoPlaceRead,
    PhotoPlaceCandidateRead,
    WantedPlaceRead,
)
from chiwawa_backend.schemas.plans import PlanDayRead, PlanDraftRead, PlanStopRead
from chiwawa_backend.schemas.schedule import ScheduleItemRead
from chiwawa_backend.schemas.trips import TripRead
from chiwawa_backend.services.wanted_places import delete_wanted_place
from chiwawa_backend.state import AppState

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
    ) as active_client:
        yield active_client


async def _create_trip(client: AsyncClient, city: str) -> TripRead:
    response = await client.post(
        "/api/v1/trips",
        json={
            "city": city,
            "start_date": "2026-07-10",
            "end_date": "2026-07-12",
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    return TripRead.model_validate_json(response.text)


async def _create_place(
    client: AsyncClient,
    trip_id: str,
    name: str,
) -> WantedPlaceRead:
    response = await client.post(
        f"/api/v1/trips/{trip_id}/wanted-places",
        json={"name": name},
    )
    assert response.status_code == HTTPStatus.CREATED
    return WantedPlaceRead.model_validate_json(response.text)


@pytest.mark.anyio
async def test_schedule_create_and_patch_reject_foreign_or_missing_place(
    client: AsyncClient,
) -> None:
    # Given: two trips and a wanted place owned only by the second trip.
    first_trip = await _create_trip(client, "Tokyo")
    second_trip = await _create_trip(client, "Osaka")
    foreign_place = await _create_place(client, second_trip.id, "Castle")
    schedule_path = f"/api/v1/trips/{first_trip.id}/schedule-items"
    base_payload = {
        "name": "Morning",
        "date": "2026-07-10",
        "start_time": "09:00:00",
        "end_time": "10:00:00",
    }

    # When: create and PATCH attempt foreign and absent place references.
    foreign_create = await client.post(
        schedule_path,
        json={**base_payload, "place_id": foreign_place.id},
    )
    missing_create = await client.post(
        schedule_path,
        json={**base_payload, "place_id": "place_missing"},
    )
    created = await client.post(schedule_path, json=base_payload)
    assert created.status_code == HTTPStatus.CREATED
    item = ScheduleItemRead.model_validate_json(created.text)
    foreign_patch = await client.patch(
        f"{schedule_path}/{item.id}",
        json={"place_id": foreign_place.id},
    )
    missing_patch = await client.patch(
        f"{schedule_path}/{item.id}",
        json={"place_id": "place_missing"},
    )

    # Then: both cases share the same non-enumerating 404 boundary.
    assert [
        response.status_code
        for response in (
            foreign_create,
            missing_create,
            foreign_patch,
            missing_patch,
        )
    ] == [HTTPStatus.NOT_FOUND] * 4


def test_delete_wanted_place_nulls_references_and_preserves_snapshots() -> None:
    # Given: one place referenced by schedule, plan, and photo confirmation caches.
    state = AppState()
    trip = TripRead(
        id="trip_refs",
        title="Tokyo",
        city="Tokyo",
        country="Japan",
        start_date=dt.date(2026, 7, 10),
        end_date=dt.date(2026, 7, 12),
        travelers=1,
        interests=[],
        travel_style=TravelStyle.BALANCED,
    )
    place = WantedPlaceRead(
        id="place_refs",
        trip_id=trip.id,
        name="Snapshot name",
        city="Tokyo",
        country="Japan",
        latitude=35.0,
        longitude=139.0,
        priority=5,
        notes=None,
        source=PlaceSource.PHOTO,
    )
    schedule = ScheduleItemRead(
        id="schedule_refs",
        trip_id=trip.id,
        name="Schedule snapshot",
        date=trip.start_date,
        start_time=dt.time(9),
        end_time=dt.time(10),
        place_id=place.id,
        notes=None,
        source=PlaceSource.PLAN,
    )
    stop = PlanStopRead(
        id="stop_refs",
        place_id=place.id,
        name="Plan snapshot",
        date=trip.start_date,
        start_time=dt.time(9),
        end_time=dt.time(10),
        notes=None,
        source=PlaceSource.PLAN,
    )
    plan = PlanDraftRead(
        id="plan_refs",
        trip_id=trip.id,
        title="Draft",
        days=[PlanDayRead(date=trip.start_date, stops=[stop])],
        estimated_total_minutes=60,
    )
    candidate = PhotoPlaceCandidateRead(
        id="candidate_refs",
        name=place.name,
        city=place.city,
        country=place.country,
        latitude=35.0,
        longitude=139.0,
        confidence=0.9,
        reason="match",
    )
    state.trips[trip.id] = trip
    state.wanted_places[place.id] = place
    state.schedule_items[schedule.id] = schedule
    state.plans[plan.id] = plan
    state.confirmed_plans.add(plan.id)
    state.confirmed_photo_places[candidate.id] = ConfirmedPhotoPlaceRead(
        search_id="search_refs",
        candidate=candidate,
        wanted_place=place,
    )

    # When: the wanted place is deleted under the aggregate lock.
    delete_wanted_place(state, trip.id, place.id)

    # Then: IDs are nulled, display snapshots survive, and stale cache is removed.
    updated_schedule = state.schedule_items[schedule.id]
    updated_stop = state.plans[plan.id].days[0].stops[0]
    assert place.id not in state.wanted_places
    assert (updated_schedule.place_id, updated_schedule.name) == (
        None,
        "Schedule snapshot",
    )
    assert (updated_stop.place_id, updated_stop.name) == (None, "Plan snapshot")
    assert candidate.id not in state.confirmed_photo_places
    assert plan.id in state.confirmed_plans
