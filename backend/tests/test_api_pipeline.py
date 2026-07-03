from __future__ import annotations

from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.base import HealthResponse, PlanJobStatus
from chiwawa_backend.schemas.memorial import MemorialRecordRead
from chiwawa_backend.schemas.places import (
    PhotoPlaceSearchResponse,
    WantedPlaceListResponse,
    WantedPlaceRead,
)
from chiwawa_backend.schemas.plans import PlanDraftRead, PlanJobRead
from chiwawa_backend.schemas.schedule import ScheduleResponse
from chiwawa_backend.schemas.travel import (
    FreeTimeRecommendationResponse,
    NearbyRecommendationResponse,
    ReplanResponse,
)
from chiwawa_backend.schemas.trips import TripListResponse, TripRead


@pytest.mark.anyio
async def test_pipeline_creates_trip_plan_schedule_and_memorial() -> None:
    # Given: a fresh backend app for the full travel-planning flow.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: the client drives the API from trip creation to memorial output.
        health_response = await client.get("/health")
        assert health_response.status_code == HTTPStatus.OK
        health = HealthResponse.model_validate(health_response.json())
        assert health.status == "ok"

        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Tokyo",
                "country": "Japan",
                "start_date": "2026-07-10",
                "end_date": "2026-07-12",
                "travelers": 2,
                "interests": ["food", "photo spots"],
                "travel_style": "balanced",
            },
        )
        assert trip_response.status_code == HTTPStatus.CREATED
        trip = TripRead.model_validate(trip_response.json())

        wanted_response = await client.post(
            f"/api/v1/trips/{trip.id}/wanted-places",
            json={
                "name": "Shibuya Sky",
                "city": "Tokyo",
                "country": "Japan",
                "priority": 5,
                "notes": "Sunset view",
            },
        )
        assert wanted_response.status_code == HTTPStatus.CREATED
        wanted_place = WantedPlaceRead.model_validate(wanted_response.json())

        photo_response = await client.post(
            f"/api/v1/trips/{trip.id}/photo-places/search",
            json={"note": "night skyline photo"},
        )
        assert photo_response.status_code == HTTPStatus.CREATED
        photo_search = PhotoPlaceSearchResponse.model_validate(photo_response.json())

        confirm_response = await client.post(
            f"/api/v1/trips/{trip.id}/photo-places/{photo_search.id}/confirm",
            json={"candidate_id": photo_search.candidates[0].id},
        )
        assert confirm_response.status_code == HTTPStatus.CREATED

        places_response = await client.get(f"/api/v1/trips/{trip.id}/wanted-places")
        assert places_response.status_code == HTTPStatus.OK
        places = WantedPlaceListResponse.model_validate(places_response.json())
        assert len(places.items) == 2

        job_response = await client.post(f"/api/v1/trips/{trip.id}/ai-plans", json={})
        assert job_response.status_code == HTTPStatus.ACCEPTED
        job = PlanJobRead.model_validate(job_response.json())
        assert job.status == PlanJobStatus.COMPLETED
        assert job.plan_id is not None

        job_status_response = await client.get(
            f"/api/v1/trips/{trip.id}/ai-plans/{job.id}",
        )
        assert job_status_response.status_code == HTTPStatus.OK

        plan_response = await client.get(f"/api/v1/trips/{trip.id}/plans/{job.plan_id}")
        assert plan_response.status_code == HTTPStatus.OK
        plan = PlanDraftRead.model_validate(plan_response.json())
        assert plan.days[0].stops[0].place_id == wanted_place.id

        confirm_plan_response = await client.post(
            f"/api/v1/trips/{trip.id}/plans/{plan.id}/confirm",
        )
        assert confirm_plan_response.status_code == HTTPStatus.CREATED

        schedule_response = await client.get(f"/api/v1/trips/{trip.id}/schedule")
        assert schedule_response.status_code == HTTPStatus.OK
        schedule = ScheduleResponse.model_validate(schedule_response.json())
        assert len(schedule.items) >= 2

        route_response = await client.post(
            f"/api/v1/trips/{trip.id}/route-optimizations",
            json={"start_place": "Hotel"},
        )
        assert route_response.status_code == HTTPStatus.CREATED
        assert route_response.json()["total_estimated_minutes"] > 0

        free_time_response = await client.post(
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations",
            json={
                "date": "2026-07-10",
                "start_time": "15:00:00",
                "end_time": "17:00:00",
                "current_area": "Shibuya",
            },
        )
        assert free_time_response.status_code == HTTPStatus.CREATED
        recommendations = FreeTimeRecommendationResponse.model_validate(
            free_time_response.json(),
        )
        add_path = (
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations/"
            f"{recommendations.items[0].id}/add"
        )
        add_response = await client.post(
            add_path,
        )
        assert add_response.status_code == HTTPStatus.CREATED

        nearby_response = await client.post(
            f"/api/v1/trips/{trip.id}/assistant/nearby",
            json={"latitude": 35.6595, "longitude": 139.7005, "theme": "food"},
        )
        assert nearby_response.status_code == HTTPStatus.CREATED
        nearby = NearbyRecommendationResponse.model_validate(nearby_response.json())
        assert nearby.items[0].title

        replan_response = await client.post(
            f"/api/v1/trips/{trip.id}/assistant/replan",
            json={"delay_minutes": 30, "reason": "train delay"},
        )
        assert replan_response.status_code == HTTPStatus.CREATED
        replan = ReplanResponse.model_validate(replan_response.json())
        assert replan.plan.id

        upload_response = await client.post(
            f"/api/v1/trips/{trip.id}/memorial/photos",
            json={
                "file_name": "tokyo-night.jpg",
                "taken_at": "2026-07-10T20:30:00",
                "latitude": 35.6595,
                "longitude": 139.7005,
                "memo": "First night view",
            },
        )
        assert upload_response.status_code == HTTPStatus.CREATED

        memorial_response = await client.post(
            f"/api/v1/trips/{trip.id}/memorial/generate",
            json={"title": "Tokyo memory"},
        )
        assert memorial_response.status_code == HTTPStatus.CREATED
        memorial = MemorialRecordRead.model_validate(memorial_response.json())
        assert memorial.photo_count == 1

        patch_memorial_response = await client.patch(
            f"/api/v1/trips/{trip.id}/memorial",
            json={"summary": "Updated travel summary"},
        )
        assert patch_memorial_response.status_code == HTTPStatus.OK

        # Then: the trip list exposes the planned trip through the API surface.
        trips_response = await client.get("/api/v1/trips")
        assert trips_response.status_code == HTTPStatus.OK
        trips = TripListResponse.model_validate(trips_response.json())
        assert trips.items[0].id == trip.id


@pytest.mark.anyio
async def test_trip_and_place_crud_returns_not_found_after_delete() -> None:
    # Given: a trip with one user-managed wanted place.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Osaka",
                "country": "Japan",
                "start_date": "2026-08-01",
                "end_date": "2026-08-03",
                "travelers": 1,
                "interests": ["cafes"],
                "travel_style": "relaxed",
            },
        )
        trip = TripRead.model_validate(trip_response.json())
        place_response = await client.post(
            f"/api/v1/trips/{trip.id}/wanted-places",
            json={"name": "Dotonbori", "city": "Osaka", "country": "Japan"},
        )
        place = WantedPlaceRead.model_validate(place_response.json())

        # When: both resources are updated and then deleted.
        trip_patch_response = await client.patch(
            f"/api/v1/trips/{trip.id}",
            json={"title": "Osaka food trip", "travelers": 2},
        )
        assert trip_patch_response.status_code == HTTPStatus.OK
        patched_trip = TripRead.model_validate(trip_patch_response.json())
        assert patched_trip.title == "Osaka food trip"

        place_patch_response = await client.patch(
            f"/api/v1/trips/{trip.id}/wanted-places/{place.id}",
            json={"priority": 4, "notes": "Dinner walk"},
        )
        assert place_patch_response.status_code == HTTPStatus.OK
        patched_place = WantedPlaceRead.model_validate(place_patch_response.json())
        assert patched_place.priority == 4

        place_delete_response = await client.delete(
            f"/api/v1/trips/{trip.id}/wanted-places/{place.id}",
        )
        assert place_delete_response.status_code == HTTPStatus.NO_CONTENT
        trip_delete_response = await client.delete(f"/api/v1/trips/{trip.id}")
        assert trip_delete_response.status_code == HTTPStatus.NO_CONTENT

        # Then: the deleted trip is no longer available.
        missing_response = await client.get(f"/api/v1/trips/{trip.id}")
        assert missing_response.status_code == HTTPStatus.NOT_FOUND
