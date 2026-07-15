from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, ValidationError

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.memorial import (
    MemorialPhotoPatchRequest,
    MemorialPhotoUploadRequest,
    MemorialUpdateRequest,
)
from chiwawa_backend.schemas.places import (
    WantedPlaceCreateRequest,
    WantedPlaceUpdateRequest,
)
from chiwawa_backend.schemas.schedule import ScheduleItemUpdateRequest
from chiwawa_backend.schemas.trips import TripUpdateRequest
from chiwawa_backend.services.jwt_auth import create_access_token
from tests.memorial_test_support import insert_user, png, settings

if TYPE_CHECKING:
    from pathlib import Path

REQUIRED_RESULT_FIELDS = [
    (TripUpdateRequest, "city"),
    (TripUpdateRequest, "country"),
    (TripUpdateRequest, "start_date"),
    (TripUpdateRequest, "end_date"),
    (TripUpdateRequest, "travelers"),
    (TripUpdateRequest, "interests"),
    (TripUpdateRequest, "travel_style"),
    (TripUpdateRequest, "title"),
    (WantedPlaceUpdateRequest, "name"),
    (WantedPlaceUpdateRequest, "city"),
    (WantedPlaceUpdateRequest, "country"),
    (WantedPlaceUpdateRequest, "priority"),
    (ScheduleItemUpdateRequest, "name"),
    (ScheduleItemUpdateRequest, "date"),
    (ScheduleItemUpdateRequest, "start_time"),
    (ScheduleItemUpdateRequest, "end_time"),
    (ScheduleItemUpdateRequest, "source"),
    (MemorialUpdateRequest, "title"),
    (MemorialUpdateRequest, "summary"),
    (MemorialPhotoPatchRequest, "taken_at"),
]
type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


def _mapping(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        message = "OpenAPI node must be an object"
        raise TypeError(message)
    return value


@pytest.mark.parametrize(
    ("model", "field"),
    REQUIRED_RESULT_FIELDS,
)
def test_patch_rejects_explicit_null_for_required_result_fields(
    model: type[BaseModel],
    field: str,
) -> None:
    # Given: a PATCH field whose persisted result is required.
    payload = {field: None}

    # When/Then: explicit null is rejected instead of becoming a silent no-op.
    with pytest.raises(ValidationError):
        _ = model.model_validate(payload)


@pytest.mark.parametrize(("model", "field"), REQUIRED_RESULT_FIELDS)
def test_openapi_marks_required_result_patch_fields_non_nullable(
    model: type[BaseModel],
    field: str,
) -> None:
    document = cast("dict[str, JsonValue]", create_app().openapi())
    components = _mapping(document["components"])
    schemas = _mapping(components["schemas"])
    model_schema = _mapping(schemas[model.__name__])
    properties = _mapping(model_schema["properties"])
    property_schema = properties[field]
    assert '"type": "null"' not in json.dumps(property_schema, sort_keys=True)


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (WantedPlaceCreateRequest, {"name": "A", "latitude": 35.0}),
        (WantedPlaceUpdateRequest, {"longitude": 139.0}),
        (MemorialPhotoUploadRequest, {"file_name": "a.jpg", "latitude": 35.0}),
        (MemorialPhotoPatchRequest, {"longitude": 139.0}),
        (MemorialPhotoPatchRequest, {"latitude": None}),
    ],
)
def test_coordinate_requests_require_a_complete_pair(
    model: type[BaseModel],
    payload: dict[str, str | float | None],
) -> None:
    # Given/When/Then: touching only one coordinate cannot create partial GPS state.
    with pytest.raises(ValidationError):
        _ = model.model_validate(payload)


@pytest.mark.anyio
async def test_member_upload_form_rejects_partial_coordinates(tmp_path: Path) -> None:
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    token = create_access_token(str(user_id), settings=active_settings)
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings=active_settings)),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/memorial/photos",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("photo.png", png(), "image/png")},
            data={"latitude": "35.0"},
        )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers["cache-control"] == "private, no-store"
