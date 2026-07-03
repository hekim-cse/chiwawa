from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from chiwawa_backend.dependencies import get_state
from chiwawa_backend.schemas.places import (
    WantedPlaceCreateRequest,
    WantedPlaceListResponse,
    WantedPlaceRead,
    WantedPlaceUpdateRequest,
)
from chiwawa_backend.services import wanted_places as wanted_place_service
from chiwawa_backend.state import AppState

router = APIRouter(prefix="/api/v1/trips/{trip_id}/wanted-places", tags=["places"])
StateDep = Annotated[AppState, Depends(get_state)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_wanted_place(
    trip_id: str,
    payload: WantedPlaceCreateRequest,
    state: StateDep,
) -> WantedPlaceRead:
    return wanted_place_service.create_wanted_place(state, trip_id, payload)


@router.get("")
def list_wanted_places(trip_id: str, state: StateDep) -> WantedPlaceListResponse:
    return wanted_place_service.list_wanted_places(state, trip_id)


@router.patch("/{place_id}")
def update_wanted_place(
    trip_id: str,
    place_id: str,
    payload: WantedPlaceUpdateRequest,
    state: StateDep,
) -> WantedPlaceRead:
    return wanted_place_service.update_wanted_place(
        state,
        trip_id,
        place_id,
        payload,
    )


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wanted_place(trip_id: str, place_id: str, state: StateDep) -> Response:
    wanted_place_service.delete_wanted_place(state, trip_id, place_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
