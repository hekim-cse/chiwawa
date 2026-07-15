from fastapi import APIRouter, Depends, Response, status

from chiwawa_backend.dependencies import (
    ActorIdDep,
    SettingsDep,
    StateDep,
    require_trip_access,
)
from chiwawa_backend.routers.responses import error_responses
from chiwawa_backend.schemas.trips import (
    TripCreateRequest,
    TripListResponse,
    TripRead,
    TripUpdateRequest,
)
from chiwawa_backend.services import trips as trip_service

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(401, 422, 500),
)
def create_trip(
    payload: TripCreateRequest,
    actor_id: ActorIdDep,
    state: StateDep,
) -> TripRead:
    return trip_service.create_trip(state, payload, actor_id)


@router.get("", responses=error_responses(401, 500))
def list_trips(
    actor_id: ActorIdDep,
    settings: SettingsDep,
    state: StateDep,
) -> TripListResponse:
    return trip_service.list_trips(
        state,
        actor_id,
        include_unowned=not settings.is_production,
    )


@router.get(
    "/{trip_id}",
    dependencies=[Depends(require_trip_access)],
    responses=error_responses(401, 404, 422, 500),
)
def get_trip(trip_id: str, state: StateDep) -> TripRead:
    return trip_service.get_trip(state, trip_id)


@router.patch(
    "/{trip_id}",
    dependencies=[Depends(require_trip_access)],
    responses=error_responses(401, 404, 422, 500),
)
def update_trip(
    trip_id: str,
    payload: TripUpdateRequest,
    state: StateDep,
) -> TripRead:
    return trip_service.update_trip(state, trip_id, payload)


@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_trip_access)],
    responses=error_responses(401, 404, 422, 500),
)
def delete_trip(trip_id: str, state: StateDep) -> Response:
    trip_service.delete_trip(state, trip_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
