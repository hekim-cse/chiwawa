from pydantic import BaseModel

COORDINATE_FIELDS = frozenset({"latitude", "longitude"})


def reject_explicit_null(
    model: BaseModel,
    required_fields: frozenset[str],
) -> None:
    for field_name in model.model_fields_set & required_fields:
        if getattr(model, field_name) is None:
            message = f"{field_name} cannot be null"
            raise ValueError(message)


def require_coordinate_pair(
    model: BaseModel,
    latitude: float | None,
    longitude: float | None,
) -> None:
    supplied = model.model_fields_set & COORDINATE_FIELDS
    if supplied and len(supplied) != len(COORDINATE_FIELDS):
        message = "latitude and longitude must be provided together"
        raise ValueError(message)
    if (latitude is None) != (longitude is None):
        message = "latitude and longitude must both be null or numeric"
        raise ValueError(message)
