from datetime import date

from chiwawa_backend.schemas.schedule import (
    ScheduleItemCreateRequest,
    ScheduleItemRead,
    ScheduleItemUpdateRequest,
    ScheduleResponse,
)
from chiwawa_backend.services.common import require_schedule_item, require_trip
from chiwawa_backend.state import AppState


def create_schedule_item(
    state: AppState,
    trip_id: str,
    payload: ScheduleItemCreateRequest,
) -> ScheduleItemRead:
    _ = require_trip(state, trip_id)
    item = ScheduleItemRead(
        id=state.next_id("schedule"),
        trip_id=trip_id,
        name=payload.name,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        place_id=payload.place_id,
        notes=payload.notes,
        source=payload.source,
    )
    state.schedule_items[item.id] = item
    return item


def list_schedule(state: AppState, trip_id: str) -> ScheduleResponse:
    _ = require_trip(state, trip_id)
    items = [item for item in state.schedule_items.values() if item.trip_id == trip_id]
    return ScheduleResponse(
        trip_id=trip_id,
        items=sorted(items, key=lambda item: (item.date, item.start_time)),
    )


def update_schedule_item(
    state: AppState,
    trip_id: str,
    item_id: str,
    payload: ScheduleItemUpdateRequest,
) -> ScheduleItemRead:
    item = require_schedule_item(state, trip_id, item_id)
    updated = ScheduleItemRead(
        id=item.id,
        trip_id=item.trip_id,
        name=payload.name or item.name,
        date=payload.date or item.date,
        start_time=payload.start_time or item.start_time,
        end_time=payload.end_time or item.end_time,
        place_id=payload.place_id if payload.place_id is not None else item.place_id,
        notes=payload.notes if payload.notes is not None else item.notes,
        source=payload.source or item.source,
    )
    state.schedule_items[item.id] = updated
    return updated


def delete_schedule_item(state: AppState, trip_id: str, item_id: str) -> None:
    _ = require_schedule_item(state, trip_id, item_id)
    del state.schedule_items[item_id]


def schedule_for_date(
    state: AppState,
    trip_id: str,
    target_date: date,
) -> ScheduleResponse:
    schedule = list_schedule(state, trip_id)
    items = [item for item in schedule.items if item.date == target_date]
    return ScheduleResponse(trip_id=trip_id, items=items)
