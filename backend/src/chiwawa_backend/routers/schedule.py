from fastapi import APIRouter, Depends, Response, status

from chiwawa_backend.dependencies import StateDep, require_trip_access
from chiwawa_backend.routers.responses import error_responses
from chiwawa_backend.schemas.schedule import (
    ScheduleItemCreateRequest,
    ScheduleItemRead,
    ScheduleItemUpdateRequest,
    ScheduleResponse,
)
from chiwawa_backend.services import schedule as schedule_service

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}",
    tags=["schedule"],
    dependencies=[Depends(require_trip_access)],
    responses=error_responses(401, 404, 422, 500),
)


@router.post(
    "/schedule-items",
    status_code=status.HTTP_201_CREATED,
)
def create_schedule_item(
    trip_id: str,
    payload: ScheduleItemCreateRequest,
    state: StateDep,
) -> ScheduleItemRead:
    return schedule_service.create_schedule_item(state, trip_id, payload)


@router.get("/schedule")
def list_schedule(trip_id: str, state: StateDep) -> ScheduleResponse:
    return schedule_service.list_schedule(state, trip_id)


@router.patch("/schedule-items/{item_id}")
def update_schedule_item(
    trip_id: str,
    item_id: str,
    payload: ScheduleItemUpdateRequest,
    state: StateDep,
) -> ScheduleItemRead:
    return schedule_service.update_schedule_item(state, trip_id, item_id, payload)


@router.delete("/schedule-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_item(trip_id: str, item_id: str, state: StateDep) -> Response:
    schedule_service.delete_schedule_item(state, trip_id, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
