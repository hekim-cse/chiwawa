from __future__ import annotations

from http import HTTPStatus
from typing import ClassVar

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, ConfigDict

from chiwawa_backend.main import create_app

type JsonValue = (
    str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
)


class OpenApiSchema(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    paths: dict[str, JsonValue]


@pytest.mark.anyio
async def test_root_redirects_to_swagger_ui() -> None:
    # Given: a fresh backend app.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: a browser opens the API root.
        response = await client.get("/")

    # Then: the user lands on the interactive Swagger UI.
    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
    assert response.headers["location"] == "/docs"


@pytest.mark.anyio
async def test_openapi_schema_exposes_current_backend_routes() -> None:
    # Given: a fresh backend app.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: the generated OpenAPI schema is requested.
        response = await client.get("/openapi.json")

    # Then: Swagger UI has the current public API surface to render.
    assert response.status_code == HTTPStatus.OK
    schema = OpenApiSchema.model_validate_json(response.text)
    expected_paths = {
        "/health",
        "/api/v1/auth/google/login",
        "/api/v1/auth/google/callback",
        "/api/v1/auth/me",
        "/api/v1/trips",
        "/api/v1/trips/{trip_id}",
        "/api/v1/trips/{trip_id}/photo-places/search",
        "/api/v1/trips/{trip_id}/photo-places/{photo_search_id}/confirm",
        "/api/v1/trips/{trip_id}/wanted-places",
        "/api/v1/trips/{trip_id}/wanted-places/{place_id}",
        "/api/v1/trips/{trip_id}/ai-plans",
        "/api/v1/trips/{trip_id}/ai-plans/{plan_job_id}",
        "/api/v1/trips/{trip_id}/plans/{plan_id}",
        "/api/v1/trips/{trip_id}/plans/{plan_id}/confirm",
        "/api/v1/trips/{trip_id}/route-optimizations",
        "/api/v1/trips/{trip_id}/schedule",
        "/api/v1/trips/{trip_id}/schedule-items",
        "/api/v1/trips/{trip_id}/schedule-items/{item_id}",
        "/api/v1/trips/{trip_id}/travel/today",
        "/api/v1/trips/{trip_id}/travel/free-time-recommendations",
        "/api/v1/trips/{trip_id}/travel/free-time-recommendations/{recommendation_id}/add",
        "/api/v1/trips/{trip_id}/assistant/nearby",
        "/api/v1/trips/{trip_id}/assistant/replan",
        "/api/v1/trips/{trip_id}/memorial",
        "/api/v1/trips/{trip_id}/memorial/photos",
        "/api/v1/trips/{trip_id}/memorial/generate",
    }
    assert expected_paths <= set(schema.paths)
