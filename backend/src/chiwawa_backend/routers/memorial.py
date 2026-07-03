from typing import Annotated

from fastapi import APIRouter, Depends, status

from chiwawa_backend.dependencies import get_state
from chiwawa_backend.schemas.memorial import (
    MemorialGenerateRequest,
    MemorialPhotoListResponse,
    MemorialPhotoRead,
    MemorialPhotoUploadRequest,
    MemorialRecordRead,
    MemorialUpdateRequest,
)
from chiwawa_backend.services import memorial as memorial_service
from chiwawa_backend.state import AppState

router = APIRouter(prefix="/api/v1/trips/{trip_id}/memorial", tags=["memorial"])
StateDep = Annotated[AppState, Depends(get_state)]


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
