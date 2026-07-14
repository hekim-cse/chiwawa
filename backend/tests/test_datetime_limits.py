from __future__ import annotations

from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.plans import PlanDraftRead, PlanJobRead
from chiwawa_backend.schemas.trips import TripRead

MAX_DATE = "9999-12-31"


async def _create_trip(
    client: AsyncClient,
    *,
    start_date: str = MAX_DATE,
    end_date: str = MAX_DATE,
) -> TripRead:
    response = await client.post(
        "/api/v1/trips",
        json={
            "city": "Tokyo",
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    return TripRead.model_validate_json(response.text)


@pytest.mark.anyio
async def test_plan_handles_maximum_calendar_date() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)
        for index in range(2):
            place_response = await client.post(
                f"/api/v1/trips/{trip.id}/wanted-places",
                json={"name": f"Late place {index}"},
            )
            assert place_response.status_code == HTTPStatus.CREATED

        job_response = await client.post(
            f"/api/v1/trips/{trip.id}/ai-plans",
            json={
                "preferred_start_time": "22:00:00",
                "preferred_end_time": "23:59:00",
                "pace": "packed",
            },
        )

        assert job_response.status_code == HTTPStatus.ACCEPTED
        job = PlanJobRead.model_validate_json(job_response.text)
        assert job.plan_id is not None
        plan_response = await client.get(
            f"/api/v1/trips/{trip.id}/plans/{job.plan_id}",
        )

    plan = PlanDraftRead.model_validate_json(plan_response.text)
    assert len(plan.days[0].stops) == 1
    assert plan.days[0].stops[0].end_time.isoformat() == "23:00:00"


@pytest.mark.anyio
async def test_replan_rejects_overflow_at_maximum_calendar_date() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)
        item_response = await client.post(
            f"/api/v1/trips/{trip.id}/schedule-items",
            json={
                "name": "Final-day stop",
                "date": MAX_DATE,
                "start_time": "23:00:00",
                "end_time": "23:30:00",
            },
        )
        assert item_response.status_code == HTTPStatus.CREATED

        response = await client.post(
            f"/api/v1/trips/{trip.id}/assistant/replan",
            json={"delay_minutes": 60},
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_replan_rejects_moving_an_item_to_another_day() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(
            client,
            start_date="2026-07-10",
            end_date="2026-07-12",
        )
        item_response = await client.post(
            f"/api/v1/trips/{trip.id}/schedule-items",
            json={
                "name": "Late stop",
                "date": "2026-07-10",
                "start_time": "23:00:00",
                "end_time": "23:30:00",
            },
        )
        assert item_response.status_code == HTTPStatus.CREATED

        response = await client.post(
            f"/api/v1/trips/{trip.id}/assistant/replan",
            json={"delay_minutes": 120},
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
