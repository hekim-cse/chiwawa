from __future__ import annotations

import time
from http import HTTPStatus
from threading import Event, Thread
from typing import TYPE_CHECKING

import anyio
import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from starlette.concurrency import run_in_threadpool

from chiwawa_backend.config import DeploymentMode, Settings
from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.trips import TripListResponse
from chiwawa_backend.services import trips as trip_service
from chiwawa_backend.services.jwt_auth import create_access_token

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.schemas.trips import TripCreateRequest, TripRead
    from chiwawa_backend.state import AppState


@pytest.mark.anyio
async def test_concurrent_http_writers_do_not_block_the_event_loop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: the first sync handler holds a production snapshot briefly.
    first_handler_started = Event()
    original_create_trip = trip_service.create_trip

    def delayed_create_trip(
        state: AppState,
        payload: TripCreateRequest,
        actor_id: int = 0,
    ) -> TripRead:
        first_handler_started.set()
        time.sleep(0.05)
        return original_create_trip(state, payload, actor_id)

    monkeypatch.setattr(trip_service, "create_trip", delayed_create_trip)
    credential = SecretStr("production-test-credential-at-least-32-characters")
    settings = Settings(
        app_env=DeploymentMode.PRODUCTION,
        database_path=tmp_path / "concurrent.db",
        memorial_photo_dir=tmp_path / "photos",
        google_client_id="client",
        google_client_secret=credential,
        google_redirect_uri="https://example.test/callback",
        google_oauth_cookie_secure=True,
        jwt_secret=credential,
        sqlite_busy_timeout_ms=200,
    )
    app = create_app(settings=settings)
    token = create_access_token("17", settings=settings)
    headers = {"Authorization": f"Bearer {token}"}
    responses: list[httpx.Response] = []
    heartbeat_delays: list[float] = []

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:

        async def post_trip(city: str) -> None:
            response = await client.post(
                "/api/v1/trips",
                headers=headers,
                json={
                    "city": city,
                    "start_date": "2026-07-10",
                    "end_date": "2026-07-11",
                },
            )
            responses.append(response)

        async def heartbeat(started_at: float) -> None:
            await anyio.sleep(0.01)
            heartbeat_delays.append(time.monotonic() - started_at)

        # When: a second writer arrives while the first request owns the transaction.
        async with anyio.create_task_group() as task_group:
            _ = task_group.start_soon(post_trip, "Tokyo")
            with anyio.fail_after(1):
                handler_started = await run_in_threadpool(
                    first_handler_started.wait,
                    1,
                )
                assert handler_started
            second_started_at = time.monotonic()
            _ = task_group.start_soon(post_trip, "Osaka")
            _ = task_group.start_soon(heartbeat, second_started_at)

        listed = await client.get("/api/v1/trips", headers=headers)
        trips = TripListResponse.model_validate_json(listed.text)

    # Then: neither SQLite waiting nor dependency teardown blocks the event loop.
    assert sorted(response.status_code for response in responses) == [
        HTTPStatus.CREATED,
        HTTPStatus.CREATED,
    ]
    assert heartbeat_delays[0] < 0.1
    assert {item.city for item in trips.items} == {"Tokyo", "Osaka"}


@pytest.mark.anyio
async def test_sixty_four_http_writers_do_not_exhaust_worker_threads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: 64 requests queue while one transaction-owning handler is held briefly.
    first_handler_started = Event()
    release_first_handler = Event()
    original_create_trip = trip_service.create_trip

    def controlled_create_trip(
        state: AppState,
        payload: TripCreateRequest,
        actor_id: int = 0,
    ) -> TripRead:
        if not first_handler_started.is_set():
            first_handler_started.set()
            _ = release_first_handler.wait(timeout=1)
        return original_create_trip(state, payload, actor_id)

    def release_after_queue_forms() -> None:
        _ = first_handler_started.wait(timeout=1)
        time.sleep(0.05)
        release_first_handler.set()

    monkeypatch.setattr(trip_service, "create_trip", controlled_create_trip)
    credential = SecretStr("production-test-credential-at-least-32-characters")
    settings = Settings(
        app_env=DeploymentMode.PRODUCTION,
        database_path=tmp_path / "stress.db",
        memorial_photo_dir=tmp_path / "photos",
        google_client_id="client",
        google_client_secret=credential,
        google_redirect_uri="https://example.test/callback",
        google_oauth_cookie_secure=True,
        jwt_secret=credential,
        sqlite_busy_timeout_ms=500,
    )
    app = create_app(settings=settings)
    token = create_access_token("17", settings=settings)
    headers = {"Authorization": f"Bearer {token}"}
    responses: list[httpx.Response] = []
    controller = Thread(target=release_after_queue_forms)
    controller.start()

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:

        async def post_trip(index: int) -> None:
            response = await client.post(
                "/api/v1/trips",
                headers=headers,
                json={
                    "city": f"City {index}",
                    "start_date": "2026-07-10",
                    "end_date": "2026-07-11",
                },
            )
            responses.append(response)

        # When: all writers arrive through one production app concurrently.
        async with anyio.create_task_group() as task_group:
            for index in range(64):
                _ = task_group.start_soon(post_trip, index)

        listed = await client.get("/api/v1/trips", headers=headers)
        trips = TripListResponse.model_validate_json(listed.text)

    controller.join(timeout=1)

    # Then: async admission leaves worker tokens for handlers and transaction cleanup.
    assert [response.status_code for response in responses] == [HTTPStatus.CREATED] * 64
    assert len(trips.items) == 64
