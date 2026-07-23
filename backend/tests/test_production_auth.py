from __future__ import annotations

from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app


@pytest.mark.anyio
async def test_production_mode_requires_authentication_for_trips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the production authentication switch is enabled.
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: an anonymous caller requests the trip collection.
        response = await client.get("/api/v1/trips")

    # Then: the protected prototype API rejects the request.
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["detail"] == "missing token"
