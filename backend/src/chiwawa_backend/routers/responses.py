from pydantic import BaseModel

from chiwawa_backend.schemas.base import ErrorResponse

type ResponseValue = str | type[BaseModel] | dict[str, ResponseValue]
type OpenApiResponses = dict[int | str, dict[str, ResponseValue]]
IMAGE_MEDIA_TYPES = (
    "image/avif",
    "image/gif",
    "image/heic",
    "image/heif",
    "image/jpeg",
    "image/png",
    "image/webp",
)


def error_responses(*status_codes: int) -> OpenApiResponses:
    return {status_code: {"model": ErrorResponse} for status_code in status_codes}


def binary_file_responses(*error_status_codes: int) -> OpenApiResponses:
    responses = error_responses(*error_status_codes)
    responses[200] = {
        "content": {
            media_type: {"schema": {"type": "string", "format": "binary"}}
            for media_type in IMAGE_MEDIA_TYPES
        }
    }
    return responses
