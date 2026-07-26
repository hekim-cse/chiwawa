# Modal Route Planner HTTP Client의 응답·오류·재시도 계약 테스트
from __future__ import annotations

import json
from typing import cast

import httpx
import pytest

from chiwawa_backend.config import Settings
from chiwawa_backend.errors import DomainValidationError, UpstreamServiceError
from chiwawa_backend.schemas.ai_planning import TripPlanningRequest
from chiwawa_backend.services.route_planner_client import RemoteRoutePlanner


def _settings(*, retries: int = 0) -> Settings:
    return Settings(
        route_planner_url="https://modal.example/plan-trip",
        route_planner_timeout_seconds=10,
        route_planner_max_retries=retries,
    )


def _request() -> TripPlanningRequest:
    return TripPlanningRequest.model_validate(
        {
            "trip_id": "trip-1",
            "timezone": "Asia/Tokyo",
            "days": [
                {
                    "day_index": 1,
                    "date": "2026-08-01",
                    "start_place": {
                        "place_id": "start",
                        "name": "도쿄역",
                        "lat": 35.6812,
                        "lng": 139.7671,
                    },
                    "start_time": "09:00",
                    "end_place": {
                        "place_id": "end",
                        "name": "시부야역",
                        "lat": 35.658,
                        "lng": 139.7016,
                    },
                    "end_time": "20:00",
                    "max_place_count": 4,
                },
            ],
            "pois": [
                {
                    "poi_id": "wanted-1",
                    "place_id": "wanted-1",
                    "name": "도쿄 타워",
                    "lat": 35.6586,
                    "lng": 139.7454,
                    "category": "ETC",
                    "estimated_stay_minutes": 90,
                    "priority": 3,
                    "must_visit": True,
                    "preferred_day_index": 1,
                },
            ],
        },
    )


def _success_payload() -> dict[str, object]:
    request = _request()
    day = request.days[0]
    poi = request.pois[0]
    return {
        "trip_id": request.trip_id,
        "status": "SUCCESS",
        "day_plans": [
            {
                "day_index": 1,
                "date": day.date.isoformat(),
                "start_place": day.start_place.model_dump(),
                "end_place": day.end_place.model_dump(),
                "assigned_pois": [poi.model_dump()],
                "estimated_total_stay_minutes": 90,
                "assignment_reason": "정확 경로 비용 기준 배정",
                "route_options": [],
            },
        ],
        "unassigned_pois": [],
        "warnings": [],
        "day_recommendations": [],
    }


@pytest.mark.anyio
async def test_client_sends_integrated_modal_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(cast("dict[str, object]", json.loads(request.content)))
        return httpx.Response(200, json=_success_payload())

    client = RemoteRoutePlanner(
        _settings(),
        transport=httpx.MockTransport(handler),
        retry_backoff_seconds=0,
    )

    response = await client.plan_trip(_request(), include_recommendations=True)

    assert response.status == "SUCCESS"
    assert captured["include_recommendations"] is True
    assert captured["timezone"] == "Asia/Tokyo"


@pytest.mark.anyio
async def test_client_maps_modal_validation_error() -> None:
    client = RemoteRoutePlanner(
        _settings(),
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(422, json={"detail": "invalid day"}),
        ),
        retry_backoff_seconds=0,
    )

    with pytest.raises(DomainValidationError, match="invalid day"):
        _ = await client.plan_trip(_request(), include_recommendations=False)


@pytest.mark.anyio
async def test_client_retries_only_transient_modal_error() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=_success_payload())

    client = RemoteRoutePlanner(
        _settings(retries=1),
        transport=httpx.MockTransport(handler),
        retry_backoff_seconds=0,
    )

    _ = await client.plan_trip(_request(), include_recommendations=False)

    assert attempts == 2


@pytest.mark.anyio
async def test_client_rejects_invalid_modal_contract() -> None:
    client = RemoteRoutePlanner(
        _settings(),
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"status": "SUCCESS"}),
        ),
        retry_backoff_seconds=0,
    )

    with pytest.raises(UpstreamServiceError, match="응답 계약"):
        _ = await client.plan_trip(_request(), include_recommendations=False)
