from __future__ import annotations

from http import HTTPStatus
from typing import ClassVar

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, ConfigDict, Field

from chiwawa_backend.main import create_app

type JsonValue = (
    str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
)


class OpenApiSchema(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    paths: dict[str, JsonValue]


class OpenApiParameter(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    name: str
    location: str = Field(alias="in")
    required: bool = False


class OpenApiOperation(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    parameters: list[OpenApiParameter] = Field(default_factory=list)
    responses: dict[str, JsonValue]
    security: list[dict[str, list[str]]] | None = None


class OpenApiPathItem(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    get: OpenApiOperation | None = None
    post: OpenApiOperation | None = None


class DetailedOpenApiSchema(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    paths: dict[str, OpenApiPathItem]


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


@pytest.mark.anyio
async def test_openapi_describes_auth_requirements_and_public_prototype_scope() -> None:
    # Given: the generated contract used by API clients.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # When: the detailed OpenAPI document is parsed.
        response = await client.get("/openapi.json")

    # Then: OAuth state and its browser-binding cookie are required, and only
    # /auth/me declares Bearer security during the public prototype stage.
    schema = DetailedOpenApiSchema.model_validate_json(response.text)
    login = schema.paths["/api/v1/auth/google/login"].get
    callback = schema.paths["/api/v1/auth/google/callback"].get
    me = schema.paths["/api/v1/auth/me"].get
    create_trip = schema.paths["/api/v1/trips"].post
    assert login is not None
    assert callback is not None
    assert me is not None
    assert create_trip is not None
    assert "302" in login.responses
    parameters = {(item.name, item.location): item for item in callback.parameters}
    assert parameters[("code", "query")].required is True
    assert parameters[("state", "query")].required is True
    assert parameters[("chiwawa_oauth_state", "cookie")].required is True
    assert {"200", "400", "422", "500", "502"} <= set(callback.responses)
    assert "401" in me.responses
    assert me.security == [{"HTTPBearer": []}]
    assert create_trip.security is None
