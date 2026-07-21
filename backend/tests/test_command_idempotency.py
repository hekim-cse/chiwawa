from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.places import (
    ConfirmedPhotoPlaceRead,
    PhotoPlaceSearchResponse,
    WantedPlaceListResponse,
)
from chiwawa_backend.schemas.schedule import ScheduleResponse
from chiwawa_backend.schemas.travel import (
    AddRecommendationResponse,
    FreeTimeRecommendationResponse,
)
from chiwawa_backend.schemas.trips import TripRead


@pytest.mark.anyio
async def test_confirmation_commands_are_idempotent() -> None:
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
                "end_date": "2026-07-10",
            },
        )
        trip = TripRead.model_validate_json(trip_response.text)

        search_response = await client.post(
            f"/api/v1/trips/{trip.id}/photo-places/search",
            json={"note": "retry-safe photo"},
        )
        search = PhotoPlaceSearchResponse.model_validate_json(search_response.text)
        confirm_path = f"/api/v1/trips/{trip.id}/photo-places/{search.id}/confirm"
        confirm_payload = {"candidate_id": search.candidates[0].id}
        first_confirm_response = await client.post(confirm_path, json=confirm_payload)
        second_confirm_response = await client.post(confirm_path, json=confirm_payload)
        places_response = await client.get(f"/api/v1/trips/{trip.id}/wanted-places")

        recommendation_response = await client.post(
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations",
            json={
                "date": "2026-07-10",
                "start_time": "15:00:00",
                "end_time": "17:00:00",
            },
        )
        recommendation = FreeTimeRecommendationResponse.model_validate_json(
            recommendation_response.text,
        ).items[0]
        add_path = (
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations/"
            f"{recommendation.id}/add"
        )
        first_add_response = await client.post(add_path)
        second_add_response = await client.post(add_path)
        schedule_response = await client.get(f"/api/v1/trips/{trip.id}/schedule")

    first_confirmation = ConfirmedPhotoPlaceRead.model_validate_json(
        first_confirm_response.text,
    )
    second_confirmation = ConfirmedPhotoPlaceRead.model_validate_json(
        second_confirm_response.text,
    )
    places = WantedPlaceListResponse.model_validate_json(places_response.text)
    assert first_confirmation.wanted_place.id == second_confirmation.wanted_place.id
    assert len(places.items) == 1

    first_add = AddRecommendationResponse.model_validate_json(first_add_response.text)
    second_add = AddRecommendationResponse.model_validate_json(second_add_response.text)
    schedule = ScheduleResponse.model_validate_json(schedule_response.text)
    assert recommendation.duration_minutes == 60
    assert first_add.schedule_item.id == second_add.schedule_item.id
    assert first_add.schedule_item.end_time.isoformat() == "16:00:00"
    assert len(schedule.items) == 1


@pytest.mark.anyio
async def test_confirm_retry_reflects_updated_wanted_place() -> None:
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
                "end_date": "2026-07-10",
            },
        )
        trip = TripRead.model_validate_json(trip_response.text)

        search_response = await client.post(
            f"/api/v1/trips/{trip.id}/photo-places/search",
            json={"note": "stale snapshot photo"},
        )
        search = PhotoPlaceSearchResponse.model_validate_json(search_response.text)
        confirm_path = f"/api/v1/trips/{trip.id}/photo-places/{search.id}/confirm"
        confirm_payload = {"candidate_id": search.candidates[0].id}
        first_confirm_response = await client.post(confirm_path, json=confirm_payload)
        first_confirmation = ConfirmedPhotoPlaceRead.model_validate_json(
            first_confirm_response.text,
        )
        place_path = (
            f"/api/v1/trips/{trip.id}/wanted-places/"
            f"{first_confirmation.wanted_place.id}"
        )

        # 확정으로 생긴 wanted place를 수정한 뒤 confirm을 재시도한다.
        patch_response = await client.patch(
            place_path,
            json={"name": "Renamed viewpoint", "priority": 2},
        )
        retry_confirm_response = await client.post(confirm_path, json=confirm_payload)
        places_response = await client.get(f"/api/v1/trips/{trip.id}/wanted-places")

        # wanted place를 삭제하면 confirm 재시도가 새로 만들어 준다.
        delete_response = await client.delete(place_path)
        recreated_response = await client.post(confirm_path, json=confirm_payload)

    assert patch_response.status_code == 200
    retried = ConfirmedPhotoPlaceRead.model_validate_json(retry_confirm_response.text)
    places = WantedPlaceListResponse.model_validate_json(places_response.text)
    assert retried.wanted_place.id == first_confirmation.wanted_place.id
    assert retried.wanted_place.name == "Renamed viewpoint"
    assert retried.wanted_place.priority == 2
    assert places.items == [retried.wanted_place]

    assert delete_response.status_code == 204
    recreated = ConfirmedPhotoPlaceRead.model_validate_json(recreated_response.text)
    assert recreated.wanted_place.id != first_confirmation.wanted_place.id
    assert recreated.wanted_place.name == first_confirmation.wanted_place.name
