from fastapi import APIRouter, Depends, status

from chiwawa_backend.dependencies import StateDep, require_trip_access
from chiwawa_backend.routers.responses import error_responses
from chiwawa_backend.schemas.places import (
    ConfirmedPhotoPlaceRead,
    PhotoPlaceConfirmRequest,
    PhotoPlaceSearchRequest,
    PhotoPlaceSearchResponse,
)
from chiwawa_backend.services import photo_places as photo_place_service

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}/photo-places",
    tags=["photo-places"],
    dependencies=[Depends(require_trip_access)],
    responses=error_responses(401, 404, 422, 500),
)


@router.post(
    "/search",
    status_code=status.HTTP_201_CREATED,
)
def search_photo_places(
    trip_id: str,
    payload: PhotoPlaceSearchRequest,
    state: StateDep,
) -> PhotoPlaceSearchResponse:
    return photo_place_service.search_photo_places(state, trip_id, payload)


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
