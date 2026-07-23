import contextlib
import json
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import ValidationError
from starlette.datastructures import FormData
from starlette.datastructures import UploadFile as StarletteUploadFile

from chiwawa_backend.config import get_settings
from chiwawa_backend.dependencies import (
    get_current_user_id,
    get_photo_place_recognizer,
    get_state,
)
from chiwawa_backend.schemas.places import (
    ConfirmedPhotoPlaceRead,
    PhotoPlaceConfirmRequest,
    PhotoPlaceSearchRequest,
    PhotoPlaceSearchResponse,
)
from chiwawa_backend.services import photo_places as photo_place_service
from chiwawa_backend.services.photo_places import (
    PhotoPlaceRecognizer,
    PhotoPlaceSearchContext,
)
from chiwawa_backend.services.photo_search_uploads import (
    MAX_PHOTO_SEARCH_UPLOAD_SIZE_BYTES,
    PHOTO_SEARCH_IMAGE_PATH,
    PhotoSearchUploadError,
    StoredPhotoSearchUpload,
    delete_photo_search_upload,
    find_photo_search_upload,
    save_photo_search_upload,
)
from chiwawa_backend.state import AppState

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}/photo-places",
    tags=["photo-places"],
)
public_router = APIRouter(prefix=PHOTO_SEARCH_IMAGE_PATH, tags=["photo-places"])
StateDep = Annotated[AppState, Depends(get_state)]
UserIdDep = Annotated[int, Depends(get_current_user_id)]
RecognizerDep = Annotated[PhotoPlaceRecognizer, Depends(get_photo_place_recognizer)]


@router.post(
    "/search",
    status_code=status.HTTP_201_CREATED,
)
async def search_photo_places(
    trip_id: str,
    request: Request,
    user_id: UserIdDep,
    state: StateDep,
    recognizer: RecognizerDep,
) -> PhotoPlaceSearchResponse:
    _ = user_id
    temporary_upload: StoredPhotoSearchUpload | None = None
    try:
        if request.headers.get("content-type", "").startswith("multipart/form-data"):
            raw_payload, temporary_upload = await _multipart_payload(request)
        else:
            raw_payload = await _json_payload(request)
        payload = _parse_payload(raw_payload)
        return await photo_place_service.search_photo_places(
            state,
            PhotoPlaceSearchContext(
                trip_id=trip_id,
                payload=payload,
                recognizer=recognizer,
            ),
        )
    finally:
        if temporary_upload is not None:
            with contextlib.suppress(OSError):
                delete_photo_search_upload(temporary_upload)


@public_router.get("/{token}", include_in_schema=False)
def download_photo_search_image(token: str) -> FileResponse:
    """Serve a temporary image while the Modal recognizer is processing it."""
    upload = find_photo_search_upload(
        token,
        get_settings().photo_search_upload_dir,
    )
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="photo search image not found",
        )
    return FileResponse(
        upload.path,
        media_type=upload.content_type,
        headers={"Cache-Control": "no-store"},
    )


@router.post(
    "/{photo_search_id}/confirm",
    status_code=status.HTTP_201_CREATED,
)
def confirm_photo_place(
    trip_id: str,
    photo_search_id: str,
    payload: PhotoPlaceConfirmRequest,
    state: StateDep,
) -> ConfirmedPhotoPlaceRead:
    return photo_place_service.confirm_photo_place(
        state,
        trip_id,
        photo_search_id,
        payload,
    )


async def _multipart_payload(
    request: Request,
) -> tuple[dict[str, object], StoredPhotoSearchUpload]:
    form = await request.form()
    file = form.get("file")
    if not isinstance(file, StarletteUploadFile):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="file is required",
        )
    try:
        data = await _read_upload(file)
    finally:
        await file.close()

    try:
        upload = save_photo_search_upload(
            data,
            get_settings().photo_search_upload_dir,
        )
    except PhotoSearchUploadError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(error),
        ) from error

    payload: dict[str, object] = {
        "image_url": (
            f"{get_settings().require_public_base_url()}"
            f"{PHOTO_SEARCH_IMAGE_PATH}/{upload.token}"
        ),
        "note": _form_text(form, "note"),
        "latitude": _form_text(form, "latitude"),
        "longitude": _form_text(form, "longitude"),
    }
    return payload, upload


async def _read_upload(file: StarletteUploadFile) -> bytes:
    chunks = bytearray()
    while chunk := await file.read(1024 * 1024):
        if len(chunks) + len(chunk) > MAX_PHOTO_SEARCH_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="photo file is too large",
            )
        chunks.extend(chunk)
    return bytes(chunks)


async def _json_payload(request: Request) -> dict[str, object]:
    try:
        raw_payload: object = cast("object", await request.json())
    except (json.JSONDecodeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="request body must be valid JSON",
        ) from error
    if not isinstance(raw_payload, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="request body must be a JSON object",
        )
    return cast("dict[str, object]", raw_payload)


def _parse_payload(raw_payload: dict[str, object]) -> PhotoPlaceSearchRequest:
    try:
        return PhotoPlaceSearchRequest.model_validate(raw_payload)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=error.errors(),
        ) from error


def _form_text(form: FormData, name: str) -> str | None:
    value = form.get(name)
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
