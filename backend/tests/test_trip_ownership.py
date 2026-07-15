from __future__ import annotations

import datetime as dt
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from chiwawa_backend.config import DeploymentMode, Settings
from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.base import TravelStyle
from chiwawa_backend.schemas.trips import TripListResponse, TripRead
from chiwawa_backend.services.jwt_auth import create_access_token
from chiwawa_backend.state import AppState

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def _production_settings(tmp_path: Path) -> Settings:
    credential = SecretStr("production-test-credential-at-least-32-characters")
    return Settings(
        app_env=DeploymentMode.PRODUCTION,
        database_path=tmp_path / "ownership.db",
        memorial_photo_dir=tmp_path / "photos",
        google_client_id="client",
        google_client_secret=credential,
        google_redirect_uri="https://example.test/callback",
        google_oauth_cookie_secure=True,
        jwt_secret=credential,
    )


def _auth_headers(user_id: int, settings: Settings) -> dict[str, str]:
    token = create_access_token(str(user_id), settings=settings)
    return {"Authorization": f"Bearer {token}"}


async def _create_trip(
    client: AsyncClient,
    headers: Mapping[str, str],
) -> TripRead:
    response = await client.post(
        "/api/v1/trips",
        headers=headers,
        json={
            "city": "Tokyo",
            "start_date": "2026-07-10",
            "end_date": "2026-07-11",
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    return TripRead.model_validate_json(response.text)


@pytest.mark.anyio
async def test_owner_can_use_trip_while_other_user_sees_not_found(
    tmp_path: Path,
) -> None:
    # Given: user A owns a production trip.
    settings = _production_settings(tmp_path)
    state = AppState()
    app = create_app(state=state, settings=settings)
    owner_headers = _auth_headers(101, settings)
    other_headers = _auth_headers(202, settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client, owner_headers)

        # When: both actors list, read, and enter the nested wanted-place boundary.
        owner_list = await client.get("/api/v1/trips", headers=owner_headers)
        owner_get = await client.get(f"/api/v1/trips/{trip.id}", headers=owner_headers)
        owner_nested = await client.post(
            f"/api/v1/trips/{trip.id}/wanted-places",
            headers=owner_headers,
            json={"name": "Shibuya Sky"},
        )
        other_list = await client.get("/api/v1/trips", headers=other_headers)
        other_get = await client.get(f"/api/v1/trips/{trip.id}", headers=other_headers)
        other_nested = await client.get(
            f"/api/v1/trips/{trip.id}/wanted-places",
            headers=other_headers,
        )
        missing = await client.get(
            "/api/v1/trips/trip_missing",
            headers=other_headers,
        )

    # Then: lists are filtered and foreign/missing IDs have one indistinguishable shape.
    owner_trips = TripListResponse.model_validate_json(owner_list.text)
    other_trips = TripListResponse.model_validate_json(other_list.text)
    assert [item.id for item in owner_trips.items] == [trip.id]
    assert owner_get.status_code == HTTPStatus.OK
    assert owner_nested.status_code == HTTPStatus.CREATED
    assert other_trips.items == []
    assert other_get.status_code == HTTPStatus.NOT_FOUND
    assert other_nested.status_code == HTTPStatus.NOT_FOUND
    assert other_get.json() == missing.json()


@pytest.mark.anyio
async def test_persistent_foreign_trip_returns_not_found(tmp_path: Path) -> None:
    # Given: production SQLite persists a trip owned by user A.
    settings = _production_settings(tmp_path)
    app = create_app(settings=settings)
    owner_headers = _auth_headers(101, settings)
    other_headers = _auth_headers(202, settings)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client, owner_headers)

        # When: user B directly addresses user A's persisted trip.
        response = await client.get(
            f"/api/v1/trips/{trip.id}",
            headers=other_headers,
        )

    # Then: rollback preserves the indistinguishable 404 instead of masking it as 500.
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"] == "trip resource not found"


@pytest.mark.anyio
async def test_trip_delete_removes_owner_and_child_resources(tmp_path: Path) -> None:
    # Given: an owned trip with a child wanted place.
    settings = _production_settings(tmp_path)
    state = AppState()
    app = create_app(state=state, settings=settings)
    headers = _auth_headers(101, settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip = await _create_trip(client, headers)
        child = await client.post(
            f"/api/v1/trips/{trip.id}/wanted-places",
            headers=headers,
            json={"name": "Shibuya Sky"},
        )

        # When: the owner deletes the aggregate.
        response = await client.delete(
            f"/api/v1/trips/{trip.id}",
            headers=headers,
        )

    # Then: both ownership and child state are removed by the same cascade.
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert trip.id not in state.trip_owners
    assert child.json()["id"] not in state.wanted_places


@pytest.mark.anyio
async def test_production_ownerless_trip_fails_closed(tmp_path: Path) -> None:
    # Given: a legacy snapshot contains a trip without ownership metadata.
    settings = _production_settings(tmp_path)
    state = AppState()
    trip = TripRead(
        id="trip_ownerless",
        title="Legacy trip",
        city="Tokyo",
        country="Japan",
        start_date=dt.date(2026, 7, 10),
        end_date=dt.date(2026, 7, 11),
        travelers=1,
        interests=[],
        travel_style=TravelStyle.BALANCED,
    )
    state.trips[trip.id] = trip
    app = create_app(state=state, settings=settings)
    headers = _auth_headers(101, settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: an authenticated actor lists and directly addresses the trip.
        listed = await client.get("/api/v1/trips", headers=headers)
        fetched = await client.get(f"/api/v1/trips/{trip.id}", headers=headers)

    # Then: production never guesses ownership for legacy data.
    assert TripListResponse.model_validate_json(listed.text).items == []
    assert fetched.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.anyio
async def test_development_uses_actor_zero_and_allows_ownerless_seed() -> None:
    # Given: development state has an ownerless directly-seeded trip.
    state = AppState()
    seeded = TripRead(
        id="trip_seeded",
        title="Seeded trip",
        city="Osaka",
        country="Japan",
        start_date=dt.date(2026, 8, 1),
        end_date=dt.date(2026, 8, 2),
        travelers=1,
        interests=[],
        travel_style=TravelStyle.BALANCED,
    )
    state.trips[seeded.id] = seeded
    app = create_app(state=state)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: anonymous development requests read the seed and create another trip.
        invalid_token_headers = {"Authorization": "Bearer invalid-development-token"}
        fetched = await client.get(
            f"/api/v1/trips/{seeded.id}",
            headers=invalid_token_headers,
        )
        created = await client.post(
            "/api/v1/trips",
            headers=invalid_token_headers,
            json={
                "city": "Kyoto",
                "start_date": "2026-08-03",
                "end_date": "2026-08-04",
            },
        )

    # Then: the legacy seed remains accessible and new trips belong to actor zero.
    created_trip = TripRead.model_validate_json(created.text)
    assert fetched.status_code == HTTPStatus.OK
    assert state.trip_owners[created_trip.id] == 0
