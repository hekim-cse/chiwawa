from typing import Annotated

from fastapi import APIRouter, Depends, status

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
from chiwawa_backend.state import AppState

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}/photo-places",
    tags=["photo-places"],
)
StateDep = Annotated[AppState, Depends(get_state)]
UserIdDep = Annotated[int, Depends(get_current_user_id)]
RecognizerDep = Annotated[PhotoPlaceRecognizer, Depends(get_photo_place_recognizer)]


@router.post(
    "/search",
    status_code=status.HTTP_201_CREATED,
)
async def search_photo_places(
    trip_id: str,
    payload: PhotoPlaceSearchRequest,
    user_id: UserIdDep,
    state: StateDep,
    recognizer: RecognizerDep,
) -> PhotoPlaceSearchResponse:
    _ = user_id
    return await photo_place_service.search_photo_places(
        state,
        PhotoPlaceSearchContext(
            trip_id=trip_id,
            payload=payload,
            recognizer=recognizer,
        ),
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
