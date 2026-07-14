from __future__ import annotations

from http import HTTPStatus
from itertools import pairwise

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.plans import (
    PlanConfirmResponse,
    PlanDraftRead,
    PlanJobRead,
)
from chiwawa_backend.schemas.schedule import ScheduleItemRead
from chiwawa_backend.schemas.travel import ReplanResponse
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


async def _create_schedule_item(  # noqa: PLR0913
    client: AsyncClient,
    trip_id: str,
    *,
    name: str,
    start_time: str,
    end_time: str,
    date: str = "2026-07-10",
) -> ScheduleItemRead:
    response = await client.post(
        f"/api/v1/trips/{trip_id}/schedule-items",
        json={
            "name": name,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    return ScheduleItemRead.model_validate_json(response.text)


async def _create_plan_with_places(
    client: AsyncClient,
    trip_id: str,
    *,
    place_count: int,
    preferred_end_time: str = "21:00:00",
) -> PlanDraftRead:
    for index in range(place_count):
        response = await client.post(
            f"/api/v1/trips/{trip_id}/wanted-places",
            json={"name": f"Place {index}", "priority": 5 - index},
        )
        assert response.status_code == HTTPStatus.CREATED

    job_response = await client.post(
        f"/api/v1/trips/{trip_id}/ai-plans",
        json={
            "preferred_start_time": "09:00:00",
            "preferred_end_time": preferred_end_time,
            "pace": "packed",
        },
    )
    assert job_response.status_code == HTTPStatus.ACCEPTED
    job = PlanJobRead.model_validate_json(job_response.text)
    assert job.plan_id is not None
    plan_response = await client.get(f"/api/v1/trips/{trip_id}/plans/{job.plan_id}")
    assert plan_response.status_code == HTTPStatus.OK
    return PlanDraftRead.model_validate_json(plan_response.text)


@pytest.mark.anyio
async def test_plan_stops_honor_preferred_window_without_overlap() -> None:
    # Given: three wanted places and a short one-day planning window.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(
            client,
            start_date="2026-07-10",
            end_date="2026-07-10",
        )

        # When: the prototype plan is generated between 09:00 and 11:00.
        plan = await _create_plan_with_places(
            client,
            trip.id,
            place_count=3,
            preferred_end_time="11:00:00",
        )

    # Then: returned stops fit the window and are sequential.
    stops = plan.days[0].stops
    assert stops
    assert all(stop.start_time >= plan.days[0].stops[0].start_time for stop in stops)
    assert all(stop.end_time.isoformat() <= "11:00:00" for stop in stops)
    assert all(
        previous.end_time <= current.start_time for previous, current in pairwise(stops)
    )


@pytest.mark.anyio
async def test_plan_confirmation_is_idempotent() -> None:
    # Given: one generated plan.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)
        plan = await _create_plan_with_places(client, trip.id, place_count=1)

        # When: the same plan is confirmed twice.
        first_response = await client.post(
            f"/api/v1/trips/{trip.id}/plans/{plan.id}/confirm",
        )
        second_response = await client.post(
            f"/api/v1/trips/{trip.id}/plans/{plan.id}/confirm",
        )

    # Then: the second request returns the original schedule projection.
    first = PlanConfirmResponse.model_validate_json(first_response.text)
    second = PlanConfirmResponse.model_validate_json(second_response.text)
    assert [item.id for item in second.schedule.items] == [
        item.id for item in first.schedule.items
    ]


@pytest.mark.anyio
async def test_replan_starts_at_current_schedule_item() -> None:
    # Given: a trip with a completed stop followed by the current stop.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)
        first = await _create_schedule_item(
            client,
            trip.id,
            name="Completed stop",
            start_time="09:00:00",
            end_time="10:00:00",
        )
        current = await _create_schedule_item(
            client,
            trip.id,
            name="Current stop",
            start_time="11:00:00",
            end_time="12:00:00",
        )

        # When: replanning begins at the second item with a 30-minute delay.
        response = await client.post(
            f"/api/v1/trips/{trip.id}/assistant/replan",
            json={"current_item_id": current.id, "delay_minutes": 30},
        )

    # Then: completed work stays fixed and only the current suffix moves.
    assert response.status_code == HTTPStatus.CREATED
    plan = ReplanResponse.model_validate_json(response.text).plan
    stops = plan.days[0].stops
    assert stops[0].name == first.name
    assert stops[0].start_time.isoformat() == "09:00:00"
    assert stops[1].start_time.isoformat() == "11:30:00"


@pytest.mark.anyio
async def test_replan_delay_does_not_shift_items_on_other_days() -> None:
    # Given: 오늘 일정과 다음날 일정이 함께 있는 여행.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)
        today_item = await _create_schedule_item(
            client,
            trip.id,
            name="Today lunch",
            start_time="10:00:00",
            end_time="11:00:00",
        )
        _ = await _create_schedule_item(
            client,
            trip.id,
            name="Tomorrow museum",
            date="2026-07-11",
            start_time="14:00:00",
            end_time="15:00:00",
        )

        # When: 오늘 항목부터 90분 지연으로 replan한다.
        response = await client.post(
            f"/api/v1/trips/{trip.id}/assistant/replan",
            json={"current_item_id": today_item.id, "delay_minutes": 90},
        )

    # Then: 오늘 항목만 밀리고 다음날 항목은 그대로여야 한다.
    assert response.status_code == HTTPStatus.CREATED
    plan = ReplanResponse.model_validate_json(response.text).plan
    stops = {stop.name: stop for day in plan.days for stop in day.stops}
    assert stops["Today lunch"].start_time.isoformat() == "11:30:00"
    assert stops["Tomorrow museum"].start_time.isoformat() == "14:00:00"
    assert stops["Tomorrow museum"].date.isoformat() == "2026-07-11"


@pytest.mark.anyio
async def test_replan_today_delay_succeeds_despite_late_item_tomorrow() -> None:
    # Given: 다음날 밤 늦은 일정이 있는 여행.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)
        today_item = await _create_schedule_item(
            client,
            trip.id,
            name="Today lunch",
            start_time="10:00:00",
            end_time="11:00:00",
        )
        _ = await _create_schedule_item(
            client,
            trip.id,
            name="Tomorrow night show",
            date="2026-07-11",
            start_time="23:00:00",
            end_time="23:30:00",
        )

        # When: 오늘 항목을 90분 미룬다 (다음날 일정과 무관해야 한다).
        response = await client.post(
            f"/api/v1/trips/{trip.id}/assistant/replan",
            json={"current_item_id": today_item.id, "delay_minutes": 90},
        )

    # Then: 다음날 밤 일정 때문에 오늘 지연이 거부되면 안 된다.
    assert response.status_code == HTTPStatus.CREATED
    plan = ReplanResponse.model_validate_json(response.text).plan
    stops = {stop.name: stop for day in plan.days for stop in day.stops}
    assert stops["Today lunch"].start_time.isoformat() == "11:30:00"
    assert stops["Tomorrow night show"].start_time.isoformat() == "23:00:00"
