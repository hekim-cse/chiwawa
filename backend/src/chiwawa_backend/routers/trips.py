from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from chiwawa_backend.dependencies import get_state, require_user_id_when_enabled
from chiwawa_backend.schemas.trips import (
    TripCreateRequest,
    TripListResponse,
    TripRead,
    TripUpdateRequest,
)
from chiwawa_backend.services import trips as trip_service
from chiwawa_backend.state import AppState

router = APIRouter(
    prefix="/api/v1/trips",
    tags=["trips"],
    dependencies=[Depends(require_user_id_when_enabled)],
)
StateDep = Annotated[AppState, Depends(get_state)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreateRequest, state: StateDep) -> TripRead:
    return trip_service.create_trip(state, payload)


@router.get("")
def list_trips(state: StateDep) -> TripListResponse:
    return trip_service.list_trips(state)


@router.get("/{trip_id}")
def get_trip(trip_id: str, state: StateDep) -> TripRead:
    return trip_service.get_trip(state, trip_id)


@router.patch("/{trip_id}")
def update_trip(
    trip_id: str,
    payload: TripUpdateRequest,
    state: StateDep,
) -> TripRead:
    return trip_service.update_trip(state, trip_id, payload)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: str, state: StateDep) -> Response:
    trip_service.delete_trip(state, trip_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
