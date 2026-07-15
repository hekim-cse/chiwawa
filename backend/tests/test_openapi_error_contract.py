from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from chiwawa_backend.main import create_app

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
RECOMMENDATION_ADD_PATH = (
    "/api/v1/trips/{trip_id}/travel/free-time-recommendations/{recommendation_id}/add"
)


class Operation(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    responses: dict[str, JsonValue]
    security: list[dict[str, list[str]]] | None = None


class PathItem(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    get: Operation | None = None
    post: Operation | None = None
    patch: Operation | None = None
    delete: Operation | None = None


class OpenApiDocument(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    paths: dict[str, PathItem]


EXPECTED_METHODS = {
    "/health": {"get"},
    "/ready": {"get"},
    "/api/v1/auth/google/login": {"get"},
    "/api/v1/auth/google/callback": {"get"},
    "/api/v1/auth/me": {"get"},
    "/api/v1/trips": {"get", "post"},
    "/api/v1/trips/{trip_id}": {"get", "patch", "delete"},
    "/api/v1/trips/{trip_id}/photo-places/search": {"post"},
    "/api/v1/trips/{trip_id}/photo-places/{photo_search_id}/confirm": {"post"},
    "/api/v1/trips/{trip_id}/wanted-places": {"get", "post"},
    "/api/v1/trips/{trip_id}/wanted-places/{place_id}": {"patch", "delete"},
    "/api/v1/trips/{trip_id}/ai-plans": {"post"},
    "/api/v1/trips/{trip_id}/ai-plans/{plan_job_id}": {"get"},
    "/api/v1/trips/{trip_id}/plans/{plan_id}": {"get"},
    "/api/v1/trips/{trip_id}/plans/{plan_id}/confirm": {"post"},
    "/api/v1/trips/{trip_id}/route-optimizations": {"post"},
    "/api/v1/trips/{trip_id}/schedule": {"get"},
    "/api/v1/trips/{trip_id}/schedule-items": {"post"},
    "/api/v1/trips/{trip_id}/schedule-items/{item_id}": {"patch", "delete"},
    "/api/v1/trips/{trip_id}/travel/today": {"get"},
    "/api/v1/trips/{trip_id}/travel/free-time-recommendations": {"post"},
    RECOMMENDATION_ADD_PATH: {"post"},
    "/api/v1/trips/{trip_id}/assistant/nearby": {"post"},
    "/api/v1/trips/{trip_id}/assistant/replan": {"post"},
    "/api/v1/trips/{trip_id}/memorial": {"get", "patch"},
    "/api/v1/trips/{trip_id}/memorial/photos": {"get", "post"},
    "/api/v1/trips/{trip_id}/memorial/generate": {"post"},
    "/api/v1/memorial/calendar": {"get"},
    "/api/v1/memorial/days/{day}": {"get"},
    "/api/v1/memorial/photos": {"post"},
    "/api/v1/memorial/photos/{photo_id}": {"get", "patch", "delete"},
    "/api/v1/memorial/photos/{photo_id}/file": {"get"},
}


def _document() -> OpenApiDocument:
    return OpenApiDocument.model_validate(create_app().openapi())


def _operations(
    document: OpenApiDocument,
) -> list[tuple[str, str, Operation]]:
    operations: list[tuple[str, str, Operation]] = []
    for path, item in document.paths.items():
        for method, operation in (
            ("get", item.get),
            ("post", item.post),
            ("patch", item.patch),
            ("delete", item.delete),
        ):
            if operation is not None:
                operations.append((path, method, operation))
    return operations


def _mapping(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        message = "OpenAPI node must be an object"
        raise TypeError(message)
    return value


def _expected_errors(path: str, method: str) -> set[str]:
    global_errors = {"400", "413", "500"}
    if path == "/health":
        errors = global_errors
    elif path == "/ready":
        errors = global_errors | {"503"}
    elif path == "/api/v1/auth/google/login":
        errors = global_errors | {"429", "503"}
    elif path == "/api/v1/auth/google/callback":
        errors = global_errors | {"422", "502"}
    elif path == "/api/v1/auth/me":
        errors = global_errors | {"401"}
    elif path == "/api/v1/trips":
        errors = global_errors | {"401"}
        errors |= {"422"} if method == "post" else set()
    elif path == "/api/v1/memorial/photos" and method == "post":
        errors = global_errors | {"401", "415", "422", "429", "507"}
    elif path in {"/api/v1/memorial/calendar", "/api/v1/memorial/days/{day}"}:
        errors = global_errors | {"401", "422"}
    elif path.startswith("/api/v1/memorial/photos/{photo_id}"):
        errors = global_errors | {"401", "404", "422"}
    else:
        errors = global_errors | {"401", "404", "422"}
    return errors


def test_openapi_path_and_method_surface_is_exact() -> None:
    document = _document()

    actual = {
        path: {
            method
            for item_path, method, _op in _operations(document)
            if item_path == path
        }
        for path in document.paths
    }

    assert actual == EXPECTED_METHODS


def test_openapi_security_and_error_matrix_is_exact() -> None:
    document = _document()

    for path, method, operation in _operations(document):
        actual_errors = {code for code in operation.responses if int(code) >= 400}
        expected_errors = _expected_errors(path, method)
        assert actual_errors == expected_errors, f"{method.upper()} {path}"
        if path.startswith(("/api/v1/trips", "/api/v1/memorial")):
            assert operation.security == [{"HTTPBearer": []}]
        for code in expected_errors:
            response = _mapping(operation.responses[code])
            content = _mapping(response["content"])
            media = _mapping(content["application/json"])
            schema = _mapping(media["schema"])
            assert schema["$ref"] == "#/components/schemas/ErrorResponse"


def test_openapi_photo_download_is_binary() -> None:
    document = _document()
    operation = document.paths["/api/v1/memorial/photos/{photo_id}/file"].get
    assert operation is not None

    response = _mapping(operation.responses["200"])
    content = _mapping(response["content"])
    assert set(content) == {
        "image/avif",
        "image/gif",
        "image/heic",
        "image/heif",
        "image/jpeg",
        "image/png",
        "image/webp",
    }
    for media_value in content.values():
        media = _mapping(media_value)
        schema = _mapping(media["schema"])
        assert schema == {"type": "string", "format": "binary"}
