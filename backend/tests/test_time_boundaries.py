from __future__ import annotations

import datetime as dt
from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.plans import AIPlanCreateRequest
from chiwawa_backend.schemas.schedule import ScheduleItemCreateRequest, ScheduleItemRead
from chiwawa_backend.schemas.travel import FreeTimeRecommendationRequest, ReplanRequest
from chiwawa_backend.schemas.trips import TripRead


async def _create_trip(client: AsyncClient) -> TripRead:
    response = await client.post(
        "/api/v1/trips",
        json={
            "city": "Tokyo",
            "start_date": "2026-07-10",
            "end_date": "2026-07-10",
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    return TripRead.model_validate_json(response.text)


def test_local_time_windows_reject_timezone_offsets() -> None:
    # Given: local travel windows mixing naive and offset-aware times.
    schedule_payload = {
        "name": "Mixed zone",
        "date": "2026-07-10",
        "start_time": "09:00:00",
        "end_time": "10:00:00+09:00",
    }
    recommendation_payload = {
        "date": "2026-07-10",
        "start_time": "09:00:00",
        "end_time": "10:00:00+09:00",
    }
    plan_payload = {
        "preferred_start_time": "09:00:00",
        "preferred_end_time": "10:00:00+09:00",
    }

    # When / Then: each local-time request rejects the offset as validation input.
    with pytest.raises(ValidationError, match="timezone offsets are not allowed"):
        _ = ScheduleItemCreateRequest.model_validate(schedule_payload)
    with pytest.raises(ValidationError, match="timezone offsets are not allowed"):
        _ = FreeTimeRecommendationRequest.model_validate(recommendation_payload)
    with pytest.raises(ValidationError, match="timezone offsets are not allowed"):
        _ = AIPlanCreateRequest.model_validate(plan_payload)


@pytest.mark.anyio
async def test_free_time_rejects_sub_minute_window() -> None:
    # Given: a valid trip and a positive window shorter than one minute.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)

        # When: the client asks for a recommendation in that window.
        response = await client.post(
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations",
            json={
                "date": "2026-07-10",
                "start_time": "10:00:30",
                "end_time": "10:00:59",
            },
        )

    # Then: the request is rejected instead of causing an internal model error.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_plan_rejects_sub_minute_window() -> None:
    # Given: a valid trip and a plan window that cannot contain a stop.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)

        # When: plan generation receives the sub-minute window.
        response = await client.post(
            f"/api/v1/trips/{trip.id}/ai-plans",
            json={
                "preferred_start_time": "09:00:00",
                "preferred_end_time": "09:00:30",
            },
        )

    # Then: request validation returns 422 rather than a zero-duration plan.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_schedule_patch_rejects_timezone_offset() -> None:
    # Given: a persisted schedule item using local naive times.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client)
        item_response = await client.post(
            f"/api/v1/trips/{trip.id}/schedule-items",
            json={
                "name": "Local stop",
                "date": "2026-07-10",
                "start_time": "09:00:00",
                "end_time": "10:00:00",
            },
        )
        item_id = ScheduleItemRead.model_validate_json(item_response.text).id

        # When: a partial update supplies an offset-aware start time.
        response = await client.patch(
            f"/api/v1/trips/{trip.id}/schedule-items/{item_id}",
            json={"start_time": "09:30:00+09:00"},
        )

    # Then: the merged service boundary rejects it instead of comparing mixed times.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_trip_rejects_duration_over_prototype_limit() -> None:
    # Given: a multi-year trip that would make planning iterate millions of dates.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: the unbounded date range is submitted.
        response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Tokyo",
                "start_date": "2026-01-01",
                "end_date": "9999-12-31",
            },
        )

    # Then: the bounded development planner rejects it at the request boundary.
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_replan_delay_has_finite_upper_bound() -> None:
    # Given: a delay too large for datetime arithmetic and a local schedule model.
    # When / Then: parsing rejects the value before a timedelta is constructed.
    with pytest.raises(ValidationError):
        _ = ReplanRequest(delay_minutes=10**100)


def test_time_window_minimum_is_one_minute() -> None:
    # Given: the exact accepted minimum duration.
    request = FreeTimeRecommendationRequest(
        date=dt.date(2026, 7, 10),
        start_time=dt.time(10),
        end_time=dt.time(10, 1),
    )

    # Then: a one-minute local window remains valid.
    assert request.end_time == dt.time(10, 1)
