from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr, ValidationError

from chiwawa_backend.config import DeploymentMode, Settings
from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.base import PlaceSource, PlanJobStatus, TravelStyle
from chiwawa_backend.schemas.memorial import MemorialPhotoRead, MemorialRecordRead
from chiwawa_backend.schemas.places import (
    ConfirmedPhotoPlaceRead,
    PhotoPlaceCandidateRead,
    PhotoPlaceSearchResponse,
    WantedPlaceRead,
)
from chiwawa_backend.schemas.plans import (
    PlanDayRead,
    PlanDraftRead,
    PlanJobRead,
    PlanStopRead,
)
from chiwawa_backend.schemas.schedule import ScheduleItemRead
from chiwawa_backend.schemas.travel import FreeTimeRecommendationRead
from chiwawa_backend.schemas.trips import TripRead
from chiwawa_backend.services.jwt_auth import create_access_token
from chiwawa_backend.services.state_store import SQLiteStateStore, StateSnapshot
from chiwawa_backend.state import AppState

if TYPE_CHECKING:
    from pathlib import Path


def _trip(trip_id: str) -> TripRead:
    return TripRead(
        id=trip_id,
        title="Tokyo trip",
        city="Tokyo",
        country="Japan",
        start_date=dt.date(2026, 7, 10),
        end_date=dt.date(2026, 7, 11),
        travelers=2,
        interests=["food"],
        travel_style=TravelStyle.BALANCED,
    )


def _complete_state() -> AppState:
    trip = _trip("trip_complete")
    candidate = PhotoPlaceCandidateRead(
        id="candidate_1",
        name="Shibuya Sky",
        city="Tokyo",
        country="Japan",
        latitude=35.66,
        longitude=139.70,
        confidence=0.9,
        reason="view",
    )
    wanted = WantedPlaceRead(
        id="place_1",
        trip_id=trip.id,
        name=candidate.name,
        city=candidate.city,
        country=candidate.country,
        latitude=candidate.latitude,
        longitude=candidate.longitude,
        priority=5,
        notes="sunset",
        source=PlaceSource.PHOTO,
    )
    stop = PlanStopRead(
        id="stop_1",
        place_id=wanted.id,
        name=wanted.name,
        date=trip.start_date,
        start_time=dt.time(9),
        end_time=dt.time(10),
        notes=None,
        source=PlaceSource.PLAN,
    )
    plan = PlanDraftRead(
        id="plan_1",
        trip_id=trip.id,
        title="Plan",
        days=[PlanDayRead(date=trip.start_date, stops=[stop])],
        estimated_total_minutes=60,
    )
    schedule_item = ScheduleItemRead(
        id="schedule_1",
        trip_id=trip.id,
        name=stop.name,
        date=stop.date,
        start_time=stop.start_time,
        end_time=stop.end_time,
        place_id=wanted.id,
        notes=None,
        source=PlaceSource.PLAN,
    )
    recommendation = FreeTimeRecommendationRead(
        id="recommendation_1",
        trip_id=trip.id,
        title="Coffee",
        place_name="Cafe",
        duration_minutes=60,
        reason="nearby",
        date=trip.start_date,
        start_time=dt.time(15),
        end_time=dt.time(16),
    )
    photo = MemorialPhotoRead(
        id="photo_1",
        trip_id=trip.id,
        file_name="view.jpg",
        taken_at=dt.datetime(2026, 7, 10, 20, tzinfo=dt.UTC),
        latitude=35.66,
        longitude=139.70,
        memo="night",
    )
    memorial = MemorialRecordRead(
        id="memorial_1",
        trip_id=trip.id,
        title="Memory",
        summary="A day",
        timeline=["Shibuya"],
        photo_count=1,
    )
    state = AppState()
    state.trips[trip.id] = trip
    state.trip_owners[trip.id] = 17
    state.photo_searches["search_1"] = PhotoPlaceSearchResponse(
        id="search_1", trip_id=trip.id, candidates=[candidate]
    )
    state.wanted_places[wanted.id] = wanted
    state.plan_jobs["job_1"] = PlanJobRead(
        id="job_1",
        trip_id=trip.id,
        status=PlanJobStatus.COMPLETED,
        plan_id=plan.id,
        message="done",
    )
    state.plans[plan.id] = plan
    state.schedule_items[schedule_item.id] = schedule_item
    state.recommendations[recommendation.id] = recommendation
    state.photos[photo.id] = photo
    state.memorials[trip.id] = memorial
    state.confirmed_plans.add(plan.id)
    state.confirmed_photo_places[candidate.id] = ConfirmedPhotoPlaceRead(
        search_id="search_1", candidate=candidate, wanted_place=wanted
    )
    state.added_recommendations[recommendation.id] = schedule_item.id
    return state


def _settings(db_path: Path) -> Settings:
    return Settings(database_path=db_path)


class _HandlerFailureError(RuntimeError):
    pass


def _fail_transaction(store: SQLiteStateStore) -> None:
    with store.transaction() as state:
        state.trips["rolled_back"] = _trip("rolled_back")
        raise _HandlerFailureError


def test_complete_state_snapshot_round_trips_losslessly() -> None:
    # Given: every durable AppState collection contains typed domain data.
    original = _complete_state()

    # When: the state crosses the Pydantic JSON storage boundary.
    restored = StateSnapshot.model_validate_json(
        StateSnapshot.from_state(original).model_dump_json()
    ).to_state()

    # Then: every durable collection survives the storage boundary.
    assert restored.trips == original.trips
    assert restored.trip_owners == original.trip_owners
    assert restored.photo_searches == original.photo_searches
    assert restored.wanted_places == original.wanted_places
    assert restored.plan_jobs == original.plan_jobs
    assert restored.plans == original.plans
    assert restored.schedule_items == original.schedule_items
    assert restored.recommendations == original.recommendations
    assert restored.photos == original.photos
    assert restored.memorials == original.memorials
    assert restored.confirmed_plans == original.confirmed_plans
    assert restored.confirmed_photo_places == original.confirmed_photo_places
    assert restored.added_recommendations == original.added_recommendations


def test_unknown_snapshot_schema_version_fails_closed() -> None:
    # Given: stored state created by an unknown future schema.
    payload = (
        StateSnapshot.from_state(AppState())
        .model_dump_json()
        .replace('"schema_version":1', '"schema_version":999')
    )

    # When/Then: validation rejects it instead of guessing a conversion.
    with pytest.raises(ValidationError):
        _ = StateSnapshot.model_validate_json(payload)


def test_state_transaction_rolls_back_on_failure(tmp_path: Path) -> None:
    # Given: an empty durable state transaction.
    store = SQLiteStateStore(_settings(tmp_path / "state.db"))

    # When: a handler mutates state and then fails.
    with pytest.raises(_HandlerFailureError):
        _fail_transaction(store)

    # Then: the failed request leaves no durable mutation.
    with store.transaction() as state:
        assert state.trips == {}


def test_two_store_instances_observe_the_same_state(tmp_path: Path) -> None:
    # Given: two workers point at one local SQLite file.
    settings = _settings(tmp_path / "shared.db")
    writer = SQLiteStateStore(settings)
    reader = SQLiteStateStore(settings)

    # When: one worker commits a trip.
    with writer.transaction() as state:
        state.trips["shared"] = _trip("shared")

    # Then: a separately constructed worker loads that trip.
    with reader.transaction() as state:
        assert state.trips["shared"].id == "shared"


def test_concurrent_state_updates_do_not_lose_data(tmp_path: Path) -> None:
    # Given: independent workers sharing the same SQLite snapshot.
    settings = _settings(tmp_path / "shared.db")
    stores = (SQLiteStateStore(settings), SQLiteStateStore(settings))

    def add_trip(item: tuple[int, SQLiteStateStore]) -> None:
        index, store = item
        trip_id = f"concurrent_{index}"
        with store.transaction() as state:
            state.trips[trip_id] = _trip(trip_id)

    # When: both workers update state concurrently.
    with ThreadPoolExecutor(max_workers=2) as executor:
        _ = list(executor.map(add_trip, enumerate(stores)))

    # Then: BEGIN IMMEDIATE serialized read-modify-write snapshots.
    with SQLiteStateStore(settings).transaction() as state:
        assert set(state.trips) == {"concurrent_0", "concurrent_1"}


@pytest.mark.anyio
async def test_production_apps_share_committed_http_state(tmp_path: Path) -> None:
    # Given: two production app instances use one absolute SQLite path.
    credential = SecretStr("production-test-credential-at-least-32-characters")
    settings = Settings(
        app_env=DeploymentMode.PRODUCTION,
        database_path=tmp_path / "production.db",
        memorial_photo_dir=tmp_path / "photos",
        google_client_id="client",
        google_client_secret=credential,
        google_redirect_uri="https://example.test/callback",
        google_oauth_cookie_secure=True,
        jwt_secret=credential,
    )
    writer_app = create_app(settings=settings)
    reader_app = create_app(settings=settings)
    token = create_access_token("17", settings=settings)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=writer_app), base_url="http://test"
    ) as writer:
        # When: the first worker creates a trip and finishes the response.
        created = await writer.post(
            "/api/v1/trips",
            headers=headers,
            json={
                "city": "Tokyo",
                "start_date": "2026-07-10",
                "end_date": "2026-07-11",
            },
        )

    async with AsyncClient(
        transport=ASGITransport(app=reader_app), base_url="http://test"
    ) as reader:
        listed = await reader.get("/api/v1/trips", headers=headers)

    # Then: function-scoped dependency teardown committed before the first response.
    assert created.status_code == HTTPStatus.CREATED
    assert listed.status_code == HTTPStatus.OK
    assert listed.json()["items"][0]["city"] == "Tokyo"
