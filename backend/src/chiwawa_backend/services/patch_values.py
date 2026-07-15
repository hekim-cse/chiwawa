from pydantic import BaseModel

from chiwawa_backend.errors import DomainValidationError


def required_patch_value[T](
    payload: BaseModel,
    field_name: str,
    supplied: T | None,
    current: T,
) -> T:
    if field_name not in payload.model_fields_set:
        return current
    if supplied is None:
        message = f"{field_name} cannot be null"
        raise DomainValidationError(message)
    return supplied


def nullable_patch_value[T](
    payload: BaseModel,
    field_name: str,
    supplied: T | None,
    current: T | None,
) -> T | None:
    if field_name in payload.model_fields_set:
        return supplied
    return current
