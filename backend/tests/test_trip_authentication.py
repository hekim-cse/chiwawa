from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Never

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from chiwawa_backend.config import DeploymentMode, Settings
from chiwawa_backend.main import create_app
from chiwawa_backend.services.jwt_auth import create_access_token
from chiwawa_backend.services.state_store import SQLiteStateStore
from chiwawa_backend.state import AppState

if TYPE_CHECKING:
    from pathlib import Path


type JsonPayload = Mapping[str, str | int | float]


@dataclass(frozen=True, slots=True)
class RequestCase:
    method: str
    path: str
    payload: JsonPayload | None = None


class StateOpenedBeforeAuthenticationError(RuntimeError):
    pass


def _reject_state_transaction(_store: SQLiteStateStore) -> Never:
    raise StateOpenedBeforeAuthenticationError


UNAUTHENTICATED_TRIP_OPERATIONS = (
    RequestCase(
        "POST",
        "/api/v1/trips",
        {
            "city": "Tokyo",
            "start_date": "2026-07-10",
            "end_date": "2026-07-11",
        },
    ),
    RequestCase("GET", "/api/v1/trips"),
    RequestCase("GET", "/api/v1/trips/trip_hidden"),
    RequestCase("PATCH", "/api/v1/trips/trip_hidden", {}),
    RequestCase("DELETE", "/api/v1/trips/trip_hidden"),
    RequestCase(
        "POST",
        "/api/v1/trips/trip_hidden/wanted-places",
        {"name": "Shibuya Sky"},
    ),
    RequestCase("GET", "/api/v1/trips/trip_hidden/wanted-places"),
    RequestCase("PATCH", "/api/v1/trips/trip_hidden/wanted-places/place_1", {}),
    RequestCase("DELETE", "/api/v1/trips/trip_hidden/wanted-places/place_1"),
    RequestCase(
        "POST",
        "/api/v1/trips/trip_hidden/photo-places/search",
        {"note": "night view"},
    ),
    RequestCase(
        "POST",
        "/api/v1/trips/trip_hidden/photo-places/search_1/confirm",
        {"candidate_id": "candidate_1"},
    ),
    RequestCase("POST", "/api/v1/trips/trip_hidden/ai-plans", {}),
    RequestCase("GET", "/api/v1/trips/trip_hidden/ai-plans/job_1"),
    RequestCase("GET", "/api/v1/trips/trip_hidden/plans/plan_1"),
    RequestCase("POST", "/api/v1/trips/trip_hidden/plans/plan_1/confirm"),
    RequestCase(
        "POST",
        "/api/v1/trips/trip_hidden/route-optimizations",
        {"start_place": "Hotel"},
    ),
    RequestCase(
        "POST",
        "/api/v1/trips/trip_hidden/schedule-items",
        {
            "name": "Breakfast",
            "date": "2026-07-10",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        },
    ),
    RequestCase("GET", "/api/v1/trips/trip_hidden/schedule"),
    RequestCase("PATCH", "/api/v1/trips/trip_hidden/schedule-items/item_1", {}),
    RequestCase("DELETE", "/api/v1/trips/trip_hidden/schedule-items/item_1"),
    RequestCase("GET", "/api/v1/trips/trip_hidden/travel/today"),
    RequestCase(
        "POST",
        "/api/v1/trips/trip_hidden/travel/free-time-recommendations",
        {
            "date": "2026-07-10",
            "start_time": "15:00:00",
            "end_time": "16:00:00",
        },
    ),
    RequestCase(
        "POST",
        "/api/v1/trips/trip_hidden/travel/free-time-recommendations/rec_1/add",
    ),
    RequestCase(
        "POST",
        "/api/v1/trips/trip_hidden/assistant/nearby",
        {"latitude": 35.6, "longitude": 139.7},
    ),
    RequestCase(
        "POST",
        "/api/v1/trips/trip_hidden/assistant/replan",
        {"delay_minutes": 10},
    ),
    RequestCase(
        "POST",
        "/api/v1/trips/trip_hidden/memorial/photos",
        {"file_name": "memory.jpg"},
    ),
    RequestCase("GET", "/api/v1/trips/trip_hidden/memorial/photos"),
    RequestCase("POST", "/api/v1/trips/trip_hidden/memorial/generate", {}),
    RequestCase("GET", "/api/v1/trips/trip_hidden/memorial"),
    RequestCase("PATCH", "/api/v1/trips/trip_hidden/memorial", {}),
)


def _production_settings(tmp_path: Path) -> Settings:
    credential = SecretStr("production-test-credential-at-least-32-characters")
    return Settings(
        app_env=DeploymentMode.PRODUCTION,
        database_path=tmp_path / "authentication.db",
        memorial_photo_dir=tmp_path / "photos",
        google_client_id="client",
        google_client_secret=credential,
        google_redirect_uri="https://example.test/callback",
        google_oauth_cookie_secure=True,
        jwt_secret=credential,
    )


@pytest.mark.anyio
@pytest.mark.parametrize("case", UNAUTHENTICATED_TRIP_OPERATIONS)
async def test_production_trip_operations_require_a_token(
    case: RequestCase,
    tmp_path: Path,
) -> None:
    # Given: a production app with every trip endpoint mounted.
    app = create_app(state=AppState(), settings=_production_settings(tmp_path))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: the operation is attempted without a bearer token.
        response = await client.request(case.method, case.path, json=case.payload)

    # Then: authentication wins over resource existence and payload processing.
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["detail"] == "missing token"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "subject",
    ["user-alice", "²", "①", "-1", "0", "9223372036854775808"],
)
async def test_production_trip_actor_rejects_invalid_integer_subject(
    subject: str,
    tmp_path: Path,
) -> None:
    # Given: a validly signed token has a subject that cannot identify a SQLite user.
    settings = _production_settings(tmp_path)
    token = create_access_token(subject, settings=settings)
    app = create_app(state=AppState(), settings=settings)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        # When: the subject is used as a trip actor.
        response = await client.get(
            "/api/v1/trips",
            headers={"Authorization": f"Bearer {token}"},
        )

    # Then: the backend rejects an identity that cannot address integer user rows.
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["detail"] == "invalid token subject"


@pytest.mark.anyio
async def test_authentication_precedes_persistent_state_transaction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: entering the shared state transaction is observable as a hard failure.
    settings = _production_settings(tmp_path)
    monkeypatch.setattr(SQLiteStateStore, "transaction", _reject_state_transaction)
    app = create_app(settings=settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: an unauthenticated actor requests the trip collection.
        response = await client.get("/api/v1/trips")

    # Then: authentication rejects the request before any SQLite write lock is entered.
    assert response.status_code == HTTPStatus.UNAUTHORIZED
