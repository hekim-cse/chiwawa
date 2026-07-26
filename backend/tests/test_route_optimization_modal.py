# Backend 경로 최적화 Endpoint와 Modal 계약 연결 테스트
from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.ai_planning import (
    TripPlanningRequest,
    TripPlanningWithRecommendationsResponse,
)
from chiwawa_backend.schemas.places import WantedPlaceRead
from chiwawa_backend.schemas.plans import RouteOptimizationResponse
from chiwawa_backend.schemas.trips import TripRead

if TYPE_CHECKING:
    import datetime as dt


class FixedTimeZoneProvider:
    async def resolve(
        self,
        *,
        latitude: float,
        longitude: float,
        date: dt.date,
    ) -> str:
        assert -90 <= latitude <= 90
        assert -180 <= longitude <= 180
        assert date.isoformat() == "2026-08-01"
        return "Asia/Tokyo"


class CapturingRoutePlanner:
    def __init__(self) -> None:
        self.request: TripPlanningRequest | None = None
        self.include_recommendations: bool | None = None

    async def plan_trip(
        self,
        request: TripPlanningRequest,
        *,
        include_recommendations: bool,
    ) -> TripPlanningWithRecommendationsResponse:
        self.request = request
        self.include_recommendations = include_recommendations
        day = request.days[0]
        poi = request.pois[0]
        return TripPlanningWithRecommendationsResponse.model_validate(
            {
                "trip_id": request.trip_id,
                "status": "SUCCESS",
                "day_plans": [
                    {
                        "day_index": day.day_index,
                        "date": day.date,
                        "start_place": day.start_place,
                        "end_place": day.end_place,
                        "assigned_pois": [poi],
                        "estimated_total_stay_minutes": 90,
                        "assignment_reason": "정확 경로 비용 기준 배정",
                        "route_options": [
                            {
                                "day_index": day.day_index,
                                "travel_mode": "TRANSIT",
                                "total_travel_minutes": 42,
                                "ordered_stops": [
                                    {
                                        "stop_type": "START",
                                        **day.start_place.model_dump(),
                                    },
                                    {
                                        "stop_type": "POI",
                                        "place_id": poi.place_id,
                                        "name": poi.name,
                                        "lat": poi.lat,
                                        "lng": poi.lng,
                                    },
                                    {
                                        "stop_type": "END",
                                        **day.end_place.model_dump(),
                                    },
                                ],
                                "route_legs": [
                                    {
                                        "origin_place_id": day.start_place.place_id,
                                        "destination_place_id": poi.place_id,
                                        "travel_minutes": 17,
                                    },
                                    {
                                        "origin_place_id": poi.place_id,
                                        "destination_place_id": day.end_place.place_id,
                                        "travel_minutes": 25,
                                    },
                                ],
                                "timeline": {
                                    "day_index": day.day_index,
                                    "travel_mode": "TRANSIT",
                                    "planned_start_at": "2026-08-01T09:00:00+09:00",
                                    "planned_end_at": "2026-08-01T20:00:00+09:00",
                                    "actual_end_at": "2026-08-01T11:12:00+09:00",
                                    "total_travel_minutes": 42,
                                    "total_stay_minutes": 90,
                                    "timeline_stops": [
                                        {
                                            "stop_type": "POI",
                                            "place_id": poi.place_id,
                                            "name": poi.name,
                                            "arrival_at": "2026-08-01T09:17:00+09:00",
                                            "departure_at": "2026-08-01T10:47:00+09:00",
                                            "stay_minutes": 90,
                                        },
                                    ],
                                },
                            },
                        ],
                    },
                ],
                "day_recommendations": [],
            },
        )


@pytest.mark.anyio
async def test_route_optimization_calls_modal_and_preserves_frontend_contract() -> None:
    planner = CapturingRoutePlanner()
    app = create_app(
        route_planner=planner,
        time_zone_provider=FixedTimeZoneProvider(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Tokyo",
                "country": "Japan",
                "start_date": "2026-08-01",
                "end_date": "2026-08-03",
            },
        )
        trip_id = TripRead.model_validate(trip_response.json()).id
        place_response = await client.post(
            f"/api/v1/trips/{trip_id}/wanted-places",
            json={
                "provider_place_id": "google-tokyo-tower",
                "name": "도쿄 타워",
                "latitude": 35.6586,
                "longitude": 139.7454,
            },
        )
        wanted_place_id = WantedPlaceRead.model_validate(place_response.json()).id
        endpoint_place_id = WantedPlaceRead.model_validate(
            (
                await client.post(
                    f"/api/v1/trips/{trip_id}/wanted-places",
                    json={
                        "provider_place_id": "tokyo-station",
                        "name": "도쿄역",
                        "latitude": 35.6812,
                        "longitude": 139.7671,
                    },
                )
            ).json(),
        ).id

        response = await client.post(
            f"/api/v1/trips/{trip_id}/route-optimizations",
            json={
                "transport_mode": "transit",
                "day_index": 1,
                "planned_start_time": "09:00",
                "planned_end_time": "20:00",
                "max_place_count": 4,
                "start": {
                    "place_id": "tokyo-station",
                    "name": "도쿄역",
                    "lat": 35.6812,
                    "lng": 139.7671,
                },
                "end": {
                    "place_id": "tokyo-station",
                    "name": "도쿄역",
                    "lat": 35.6812,
                    "lng": 139.7671,
                },
                "wanted_place_ids": [endpoint_place_id, wanted_place_id],
                "pace": "balanced",
                "include_recommendations": True,
            },
        )
        confirm_response = await client.post(
            f"/api/v1/trips/{trip_id}/route-optimizations/confirm",
            json={"timeline": response.json()["timeline"]},
        )
        schedule_response = await client.get(
            f"/api/v1/trips/{trip_id}/schedule",
        )
        confirmed_routes_response = await client.get(
            f"/api/v1/trips/{trip_id}/route-optimizations/confirmed",
        )

    assert response.status_code == HTTPStatus.CREATED
    body = RouteOptimizationResponse.model_validate(response.json())
    assert body.transport_mode == "transit"
    assert body.stops[0].place_id == wanted_place_id
    assert body.stops[0].name == "도쿄 타워"
    assert body.stops[0].estimated_travel_minutes == 17
    assert body.timeline is not None
    assert body.timeline.timeline_stops[0].place_id == wanted_place_id
    assert body.timeline.total_stay_minutes == 90
    assert planner.request is not None
    assert planner.request.days[0].date.isoformat() == "2026-08-01"
    assert planner.request.timezone == "Asia/Tokyo"
    assert planner.request.days[0].start_place.place_id == "tokyo-station"
    assert planner.request.days[0].end_place.place_id.startswith("chiwawa:end:1:")
    assert planner.request.days[0].end_place.lat == 35.6812
    assert planner.request.days[0].end_place.lng == 139.7671
    assert planner.request.pois[0].place_id == "google-tokyo-tower"
    assert len(planner.request.pois) == 1
    assert planner.request.pois[0].preferred_day_index == 1
    assert planner.include_recommendations is True
    assert confirm_response.status_code == HTTPStatus.OK
    assert confirmed_routes_response.status_code == HTTPStatus.OK
    confirmed_route = confirmed_routes_response.json()["items"][0]
    assert confirmed_route["start"]["name"] == "도쿄역"
    assert confirmed_route["end"]["name"] == "도쿄역"
    assert confirmed_route["route"]["timeline"] == response.json()["timeline"]
    schedule = schedule_response.json()["items"]
    assert len(schedule) == 1
    assert schedule[0]["name"] == "도쿄 타워"
    assert schedule[0]["source"] == "plan"


@pytest.mark.anyio
async def test_route_optimization_rejects_place_without_coordinates() -> None:
    planner = CapturingRoutePlanner()
    app = create_app(
        route_planner=planner,
        time_zone_provider=FixedTimeZoneProvider(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = TripRead.model_validate(
            (
                await client.post(
                    "/api/v1/trips",
                    json={
                        "city": "Tokyo",
                        "country": "Japan",
                        "start_date": "2026-08-01",
                        "end_date": "2026-08-01",
                    },
                )
            ).json(),
        )
        place = WantedPlaceRead.model_validate(
            (
                await client.post(
                    f"/api/v1/trips/{trip.id}/wanted-places",
                    json={"name": "좌표 없는 장소"},
                )
            ).json(),
        )
        response = await client.post(
            f"/api/v1/trips/{trip.id}/route-optimizations",
            json={
                "start": {
                    "place_id": "start",
                    "name": "도쿄역",
                    "lat": 35.6812,
                    "lng": 139.7671,
                },
                "end": {
                    "place_id": "end",
                    "name": "시부야역",
                    "lat": 35.658,
                    "lng": 139.7016,
                },
                "wanted_place_ids": [place.id],
            },
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "장소 좌표" in response.json()["detail"]
    assert planner.request is None


@pytest.mark.anyio
async def test_route_optimization_rejects_recommendations_without_place_id() -> None:
    """추천 지표에 필요한 Google Place ID 누락을 Modal 호출 전에 차단한다."""
    planner = CapturingRoutePlanner()
    app = create_app(
        route_planner=planner,
        time_zone_provider=FixedTimeZoneProvider(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = TripRead.model_validate(
            (
                await client.post(
                    "/api/v1/trips",
                    json={
                        "city": "Tokyo",
                        "country": "Japan",
                        "start_date": "2026-08-01",
                        "end_date": "2026-08-01",
                    },
                )
            ).json(),
        )
        place = WantedPlaceRead.model_validate(
            (
                await client.post(
                    f"/api/v1/trips/{trip.id}/wanted-places",
                    json={
                        "name": "도쿄 타워",
                        "latitude": 35.6586,
                        "longitude": 139.7454,
                    },
                )
            ).json(),
        )
        response = await client.post(
            f"/api/v1/trips/{trip.id}/route-optimizations",
            json={
                "start": {
                    "place_id": "google-start",
                    "name": "도쿄역",
                    "lat": 35.6812,
                    "lng": 139.7671,
                },
                "end": {
                    "place_id": "google-end",
                    "name": "시부야역",
                    "lat": 35.658,
                    "lng": 139.7016,
                },
                "wanted_place_ids": [place.id],
                "include_recommendations": True,
            },
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "Google Place ID" in response.json()["detail"]
    assert planner.request is None
