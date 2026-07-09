import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from chiwawa_backend.dependencies import get_current_user_id, get_state
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
from chiwawa_backend.state import AppState

router = APIRouter(prefix="/api/v1/trips/{trip_id}/memorial", tags=["memorial"])
StateDep = Annotated[AppState, Depends(get_state)]

album_router = APIRouter(prefix="/api/v1/memorial", tags=["memorial"])
UserIdDep = Annotated[int, Depends(get_current_user_id)]


@album_router.post("/photos", status_code=status.HTTP_201_CREATED)
async def upload_memorial_photo(  # noqa: PLR0913
    user_id: UserIdDep,
    file: Annotated[UploadFile, File()],
    taken_at: Annotated[dt.datetime | None, Form()] = None,
    latitude: Annotated[float | None, Form(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Form(ge=-180, le=180)] = None,
    memo: Annotated[str | None, Form()] = None,
) -> MemorialPhotoItem:
    data = await file.read()
    upload = PhotoUpload(
        file_name=file.filename or "photo",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        taken_at=taken_at,
        latitude=latitude,
        longitude=longitude,
        memo=memo,
    )
    return memorial_photos.save_photo(user_id, upload)


@album_router.get("/calendar")
def memorial_calendar(
    user_id: UserIdDep,
    year: Annotated[int, Query(ge=2000, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
) -> MemorialCalendarResponse:
    return memorial_photos.month_calendar(user_id, year, month)


@album_router.get("/days/{day}")
def memorial_day_timeline(day: dt.date, user_id: UserIdDep) -> MemorialDayResponse:
    return memorial_photos.day_timeline(user_id, day)


@album_router.get("/photos/{photo_id}")
def get_memorial_photo(photo_id: int, user_id: UserIdDep) -> MemorialPhotoItem:
    return memorial_photos.get_photo(user_id, photo_id)


@album_router.get("/photos/{photo_id}/file")
def download_memorial_photo(photo_id: int, user_id: UserIdDep) -> FileResponse:
    path, content_type = memorial_photos.photo_file(user_id, photo_id)
    return FileResponse(path, media_type=content_type)


@album_router.patch("/photos/{photo_id}")
def patch_memorial_photo(
    photo_id: int,
    payload: MemorialPhotoPatchRequest,
    user_id: UserIdDep,
) -> MemorialPhotoItem:
    return memorial_photos.update_photo(user_id, photo_id, payload)


@album_router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memorial_photo(photo_id: int, user_id: UserIdDep) -> None:
    memorial_photos.delete_photo(user_id, photo_id)


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
