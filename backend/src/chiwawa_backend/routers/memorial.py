import datetime as dt
import io
from typing import Annotated, Final

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool

from chiwawa_backend.dependencies import (
    SettingsDep,
    StateDep,
    get_current_user_id,
    require_trip_access,
)
from chiwawa_backend.errors import DomainValidationError, PayloadTooLargeError
from chiwawa_backend.routers.responses import (
    binary_file_responses,
    error_responses,
)
from chiwawa_backend.schemas.memorial import (
    MemorialCalendarResponse,
    MemorialDayResponse,
    MemorialGenerateRequest,
    MemorialPhotoItem,
    MemorialPhotoListResponse,
    MemorialPhotoPatchRequest,
    MemorialPhotoRead,
    MemorialPhotoUploadRequest,
    MemorialRecordRead,
    MemorialUpdateRequest,
)
from chiwawa_backend.services import memorial as memorial_service
from chiwawa_backend.services import memorial_photos
from chiwawa_backend.services.memorial_photos import PhotoUpload

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}/memorial",
    tags=["memorial"],
    dependencies=[Depends(require_trip_access)],
    responses=error_responses(401, 404, 422, 500),
)

MAX_MEMORIAL_PHOTO_SIZE_BYTES: Final = 10 * 1024 * 1024
UPLOAD_READ_CHUNK_SIZE_BYTES: Final = 1024 * 1024
PRIVATE_CACHE_CONTROL: Final = "private, no-store"
PHOTO_TOO_LARGE_DETAIL: Final = "photo file is too large"
COORDINATE_PAIR_DETAIL: Final = "latitude and longitude must be provided together"

album_router = APIRouter(
    prefix="/api/v1/memorial",
    tags=["memorial"],
    responses=error_responses(401, 422, 500),
)
UserIdDep = Annotated[int, Depends(get_current_user_id)]


@album_router.post(
    "/photos",
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(413, 415, 429, 507),
)
async def upload_memorial_photo(  # noqa: PLR0913
    user_id: UserIdDep,
    settings: SettingsDep,
    response: Response,
    file: Annotated[UploadFile, File()],
    taken_at: Annotated[dt.datetime | None, Form()] = None,
    latitude: Annotated[float | None, Form(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Form(ge=-180, le=180)] = None,
    memo: Annotated[
        str | None,
        Form(max_length=memorial_photos.MAX_MEMO_CHARS),
    ] = None,
) -> MemorialPhotoItem:
    _require_paired_coordinates(latitude, longitude)
    file_name = file.filename or "photo"
    if len(file_name) > memorial_photos.MAX_FILE_NAME_CHARS:
        message = "photo file name is too long"
        raise DomainValidationError(message)
    buffer = io.BytesIO()
    total_size = 0
    while chunk := await file.read(UPLOAD_READ_CHUNK_SIZE_BYTES):
        total_size += len(chunk)
        if total_size > settings.max_photo_bytes:
            raise PayloadTooLargeError(PHOTO_TOO_LARGE_DETAIL)
        _ = buffer.write(chunk)
    data = buffer.getvalue()
    upload = PhotoUpload(
        file_name=file_name,
        content_type=file.content_type or "application/octet-stream",
        data=data,
        taken_at=taken_at,
        latitude=latitude,
        longitude=longitude,
        memo=memo,
    )
    _set_private(response)
    return await run_in_threadpool(
        memorial_photos.save_photo,
        user_id,
        upload,
        settings=settings,
    )


@album_router.get("/calendar")
def memorial_calendar(
    user_id: UserIdDep,
    settings: SettingsDep,
    response: Response,
    year: Annotated[int, Query(ge=2000, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
) -> MemorialCalendarResponse:
    _set_private(response)
    return memorial_photos.month_calendar(user_id, year, month, settings=settings)


@album_router.get("/days/{day}")
def memorial_day_timeline(
    day: dt.date,
    user_id: UserIdDep,
    settings: SettingsDep,
    response: Response,
) -> MemorialDayResponse:
    _set_private(response)
    return memorial_photos.day_timeline(user_id, day, settings=settings)


@album_router.get("/photos/{photo_id}", responses=error_responses(404))
def get_memorial_photo(
    photo_id: int,
    user_id: UserIdDep,
    settings: SettingsDep,
    response: Response,
) -> MemorialPhotoItem:
    _set_private(response)
    return memorial_photos.get_photo(user_id, photo_id, settings=settings)


@album_router.get(
    "/photos/{photo_id}/file",
    response_class=Response,
    responses=binary_file_responses(404),
)
def download_memorial_photo(
    photo_id: int,
    user_id: UserIdDep,
    settings: SettingsDep,
) -> Response:
    data, content_type = memorial_photos.photo_file(
        user_id,
        photo_id,
        settings=settings,
    )
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": PRIVATE_CACHE_CONTROL},
    )


@album_router.patch("/photos/{photo_id}", responses=error_responses(404))
def patch_memorial_photo(
    photo_id: int,
    payload: MemorialPhotoPatchRequest,
    user_id: UserIdDep,
    settings: SettingsDep,
    response: Response,
) -> MemorialPhotoItem:
    _set_private(response)
    return memorial_photos.update_photo(
        user_id,
        photo_id,
        payload,
        settings=settings,
    )


@album_router.delete(
    "/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(404),
)
def delete_memorial_photo(
    photo_id: int,
    user_id: UserIdDep,
    settings: SettingsDep,
    response: Response,
) -> None:
    _set_private(response)
    memorial_photos.delete_photo(user_id, photo_id, settings=settings)


def _set_private(response: Response) -> None:
    response.headers["Cache-Control"] = PRIVATE_CACHE_CONTROL


def _require_paired_coordinates(
    latitude: float | None,
    longitude: float | None,
) -> None:
    if (latitude is None) != (longitude is None):
        raise DomainValidationError(COORDINATE_PAIR_DETAIL)


@router.post(
    "/photos",
    status_code=status.HTTP_201_CREATED,
)
def upload_photo(
    trip_id: str,
    payload: MemorialPhotoUploadRequest,
    state: StateDep,
) -> MemorialPhotoRead:
    return memorial_service.upload_photo(state, trip_id, payload)


@router.get("/photos")
def list_photos(trip_id: str, state: StateDep) -> MemorialPhotoListResponse:
    return memorial_service.list_photos(state, trip_id)


@router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
)
def generate_memorial(
    trip_id: str,
    payload: MemorialGenerateRequest,
    state: StateDep,
) -> MemorialRecordRead:
    return memorial_service.generate_memorial(state, trip_id, payload)


@router.get("")
def get_memorial(trip_id: str, state: StateDep) -> MemorialRecordRead:
    return memorial_service.get_memorial(state, trip_id)


@router.patch("")
def update_memorial(
    trip_id: str,
    payload: MemorialUpdateRequest,
    state: StateDep,
) -> MemorialRecordRead:
    return memorial_service.update_memorial(state, trip_id, payload)
