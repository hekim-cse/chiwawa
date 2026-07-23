from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from ai.image_search.services.image_loader import detect_image_mime_type

from chiwawa_backend.services.exif import InvalidImageError, validate_image

if TYPE_CHECKING:
    from pathlib import Path

PHOTO_SEARCH_IMAGE_PATH = "/api/v1/photo-search-images"
MAX_PHOTO_SEARCH_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
_TOKEN_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_MIME_SUFFIXES = {
    "image/gif": ".gif",
    "image/heic": ".heic",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@dataclass(frozen=True, slots=True)
class StoredPhotoSearchUpload:
    token: str
    path: Path
    content_type: str


class PhotoSearchUploadError(ValueError):
    """Raised when an uploaded photo is not a supported valid image."""

    INVALID_IMAGE: str = "uploaded file is not a valid image"
    UNSUPPORTED_FORMAT: str = "unsupported image format"


def save_photo_search_upload(
    data: bytes,
    directory: Path,
) -> StoredPhotoSearchUpload:
    """Validate and persist one temporary photo-search upload."""
    try:
        validate_image(data)
    except InvalidImageError as error:
        raise PhotoSearchUploadError(PhotoSearchUploadError.INVALID_IMAGE) from error

    content_type = detect_image_mime_type(data)
    suffix = _MIME_SUFFIXES.get(content_type)
    if suffix is None:
        raise PhotoSearchUploadError(PhotoSearchUploadError.UNSUPPORTED_FORMAT)

    token = uuid4().hex
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{token}{suffix}"
    _ = path.write_bytes(data)
    return StoredPhotoSearchUpload(
        token=token,
        path=path,
        content_type=content_type,
    )


def find_photo_search_upload(
    token: str,
    directory: Path,
) -> StoredPhotoSearchUpload | None:
    """Resolve a random upload token to a stored image without path traversal."""
    if _TOKEN_PATTERN.fullmatch(token) is None:
        return None
    for content_type, suffix in _MIME_SUFFIXES.items():
        path = directory / f"{token}{suffix}"
        if path.is_file():
            return StoredPhotoSearchUpload(
                token=token,
                path=path,
                content_type=content_type,
            )
    return None


def delete_photo_search_upload(upload: StoredPhotoSearchUpload) -> None:
    """Delete a temporary photo-search upload after the remote call finishes."""
    upload.path.unlink(missing_ok=True)
