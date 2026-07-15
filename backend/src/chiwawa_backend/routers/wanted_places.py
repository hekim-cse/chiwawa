from fastapi import APIRouter, Depends, Response, status

from chiwawa_backend.dependencies import StateDep, require_trip_access
from chiwawa_backend.routers.responses import error_responses
from chiwawa_backend.schemas.places import (
    WantedPlaceCreateRequest,
    WantedPlaceListResponse,
    WantedPlaceRead,
    WantedPlaceUpdateRequest,
)
from chiwawa_backend.services import wanted_places as wanted_place_service

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}/wanted-places",
    tags=["places"],
    dependencies=[Depends(require_trip_access)],
    responses=error_responses(401, 404, 422, 500),
)


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
