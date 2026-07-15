from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from chiwawa_backend.config import Settings
from chiwawa_backend.main import create_app
from chiwawa_backend.routers import auth as auth_router
from chiwawa_backend.services.oauth_state_store import (
    OAuthStateCapacityError,
    OAuthStateCollisionError,
    OAuthStateConfigurationError,
    OAuthStateStore,
    OAuthStateTimeError,
)

if TYPE_CHECKING:
    from pathlib import Path


def _settings(db_path: Path) -> Settings:
    return Settings(database_path=db_path)


def test_state_issued_by_one_store_is_consumed_by_another(tmp_path: Path) -> None:
    # Given: two workers share one OAuth state table.
    settings = _settings(tmp_path / "oauth.db")
    issuer = OAuthStateStore(settings)
    consumer = OAuthStateStore(settings)
    now = datetime.now(UTC)
    issuer.issue("handoff", now + timedelta(minutes=5))

    # When: the callback lands on the second worker.
    consumed = consumer.consume("handoff", now)

    # Then: the state is shared and one-shot.
    assert consumed is True
    assert issuer.consume("handoff", now) is False


def test_concurrent_consumers_have_exactly_one_success(tmp_path: Path) -> None:
    # Given: one valid state and several independent consumers.
    settings = _settings(tmp_path / "oauth.db")
    now = datetime.now(UTC)
    OAuthStateStore(settings).issue("single-use", now + timedelta(minutes=5))
    stores = [OAuthStateStore(settings) for _ in range(8)]

    def consume(store: OAuthStateStore) -> bool:
        return store.consume("single-use", now)

    # When: callbacks race to consume the same state.
    with ThreadPoolExecutor(max_workers=len(stores)) as executor:
        results = list(executor.map(consume, stores))

    # Then: the atomic delete permits exactly one callback.
    assert results.count(True) == 1


def test_state_is_invalid_at_exact_expiration(tmp_path: Path) -> None:
    # Given: an OAuth state with a known expiry instant.
    store = OAuthStateStore(_settings(tmp_path / "oauth.db"))
    expires_at = datetime.now(UTC) + timedelta(minutes=1)
    store.issue("expires", expires_at)

    # When/Then: equality is expired, not valid for one extra instant.
    assert store.consume("expires", expires_at) is False


def test_purge_removes_only_expired_states(tmp_path: Path) -> None:
    # Given: one expired state and one valid state.
    store = OAuthStateStore(_settings(tmp_path / "oauth.db"))
    now = datetime.now(UTC) + timedelta(minutes=1)
    store.issue("expired", now)
    store.issue("valid", now + timedelta(minutes=1))

    # When: scheduled cleanup runs at the boundary instant.
    removed = store.purge(now)

    # Then: only expired state is deleted.
    assert removed == 1
    assert store.consume("valid", now) is True


def test_capacity_rejection_does_not_evict_valid_states(tmp_path: Path) -> None:
    # Given: the OAuth table is full of valid states.
    store = OAuthStateStore(_settings(tmp_path / "oauth.db"), capacity=2)
    now = datetime.now(UTC)
    store.issue("first", now + timedelta(minutes=1))
    store.issue("second", now + timedelta(minutes=1))

    # When: another login attempts to issue state.
    with pytest.raises(OAuthStateCapacityError):
        store.issue("rejected", now + timedelta(minutes=1))

    # Then: both previously valid states remain consumable.
    assert store.consume("first", now) is True
    assert store.consume("second", now) is True
    assert store.consume("rejected", now) is False


def test_non_positive_capacity_is_rejected_at_construction(tmp_path: Path) -> None:
    # Given: an invalid OAuth state capacity.
    settings = _settings(tmp_path / "oauth.db")

    # When/Then: the store rejects an unusable configuration immediately.
    with pytest.raises(OAuthStateConfigurationError):
        _ = OAuthStateStore(settings, capacity=0)


def test_naive_oauth_timestamp_is_rejected(tmp_path: Path) -> None:
    # Given: a timestamp without a UTC offset.
    store = OAuthStateStore(_settings(tmp_path / "oauth.db"))
    naive_expiration = datetime(2026, 7, 14, 12, tzinfo=UTC).replace(tzinfo=None)

    # When/Then: persistence fails closed instead of using the host timezone.
    with pytest.raises(OAuthStateTimeError):
        store.issue("naive", naive_expiration)


def test_duplicate_oauth_state_collision_does_not_overwrite(tmp_path: Path) -> None:
    # Given: a valid state value already exists.
    store = OAuthStateStore(_settings(tmp_path / "oauth.db"))
    now = datetime.now(UTC)
    store.issue("duplicate", now + timedelta(minutes=1))

    # When: another issue attempt collides with the same random value.
    with pytest.raises(OAuthStateCollisionError):
        store.issue("duplicate", now + timedelta(minutes=5))

    # Then: the original state remains valid and one-shot.
    assert store.consume("duplicate", now) is True


@pytest.mark.anyio
async def test_login_retries_random_oauth_state_collision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: the first generated login state collides and the second is unique.
    settings = Settings(
        database_path=tmp_path / "oauth.db",
        google_client_id="client",
        google_client_secret=SecretStr("provider-secret"),
        google_redirect_uri="http://test/api/v1/auth/google/callback",
    )
    store = OAuthStateStore(settings)
    collision = "x" * 43
    replacement = "y" * 43
    store.issue(collision, datetime.now(UTC) + timedelta(minutes=5))
    generated = iter((collision, replacement))

    def next_state(_byte_count: int) -> str:
        return next(generated)

    monkeypatch.setattr(auth_router, "token_urlsafe", next_state)
    app = create_app(settings=settings, oauth_state_store=store)

    # When: a browser starts login during the collision.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/auth/google/login", follow_redirects=False)

    # Then: login succeeds with a newly generated state rather than 429 or 500.
    state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    assert response.status_code == HTTPStatus.FOUND
    assert state == replacement


@pytest.mark.anyio
async def test_login_returns_service_unavailable_after_three_collisions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: every generated state collides with one already stored value.
    settings = Settings(
        database_path=tmp_path / "oauth.db",
        google_client_id="client",
        google_client_secret=SecretStr("provider-secret"),
        google_redirect_uri="http://test/api/v1/auth/google/callback",
    )
    store = OAuthStateStore(settings)
    collision = "x" * 43
    store.issue(collision, datetime.now(UTC) + timedelta(minutes=5))
    attempts = 0

    def colliding_state(_count: int) -> str:
        nonlocal attempts
        attempts += 1
        return collision

    monkeypatch.setattr(auth_router, "token_urlsafe", colliding_state)
    app = create_app(settings=settings, oauth_state_store=store)

    # When: login exhausts its bounded collision retries.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/auth/google/login")

    # Then: the route returns an explicit retryable error, not 429 or 500.
    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert attempts == 3


def test_concurrent_issue_at_capacity_has_one_winner(tmp_path: Path) -> None:
    # Given: two workers race for the only OAuth state slot.
    settings = _settings(tmp_path / "oauth.db")
    stores = (
        OAuthStateStore(settings, capacity=1),
        OAuthStateStore(settings, capacity=1),
    )
    expires_at = datetime.now(UTC) + timedelta(minutes=5)

    def issue(item: tuple[int, OAuthStateStore]) -> str:
        index, store = item
        value = f"state-{index}"
        try:
            store.issue(value, expires_at)
        except OAuthStateCapacityError:
            return "capacity"
        return "issued"

    # When: both issue transactions start concurrently.
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(issue, enumerate(stores)))

    # Then: BEGIN IMMEDIATE admits one value and rejects the other without eviction.
    assert sorted(outcomes) == ["capacity", "issued"]


@pytest.mark.anyio
async def test_login_maps_oauth_capacity_to_too_many_requests(tmp_path: Path) -> None:
    # Given: an injected store whose only slot already contains valid state.
    credential = SecretStr("test-credential")
    settings = Settings(
        database_path=tmp_path / "oauth.db",
        google_client_id="client",
        google_client_secret=credential,
        google_redirect_uri="http://test/api/v1/auth/google/callback",
    )
    store = OAuthStateStore(settings, capacity=1)
    store.issue("occupied", datetime.now(UTC) + timedelta(minutes=5))
    app = create_app(settings=settings, oauth_state_store=store)

    # When: another browser starts OAuth login.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/auth/google/login")

    # Then: load shedding is explicit and valid state is preserved.
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert store.consume("occupied", datetime.now(UTC)) is True
