from datetime import date, time

from chiwawa_backend.errors import DomainValidationError
from chiwawa_backend.schemas.schedule import (
    ScheduleItemCreateRequest,
    ScheduleItemRead,
    ScheduleItemUpdateRequest,
    ScheduleResponse,
)
from chiwawa_backend.services.common import (
    require_schedule_item,
    require_trip,
    require_wanted_place,
)
from chiwawa_backend.services.patch_values import (
    nullable_patch_value,
    required_patch_value,
)
from chiwawa_backend.state import AppState, synchronized

SCHEDULE_DATE_ERROR = "schedule date must be within trip dates"
SCHEDULE_TIME_ERROR = "end_time must be after start_time"
SCHEDULE_TIMEZONE_ERROR = "timezone offsets are not allowed"


@synchronized
def create_schedule_item(
    state: AppState,
    trip_id: str,
    payload: ScheduleItemCreateRequest,
) -> ScheduleItemRead:
    validate_schedule_item(state, trip_id, payload)
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


@synchronized
def list_schedule(state: AppState, trip_id: str) -> ScheduleResponse:
    _ = require_trip(state, trip_id)
    items = [item for item in state.schedule_items.values() if item.trip_id == trip_id]
    return ScheduleResponse(
        trip_id=trip_id,
        items=sorted(items, key=lambda item: (item.date, item.start_time)),
    )


@synchronized
def update_schedule_item(
    state: AppState,
    trip_id: str,
    item_id: str,
    payload: ScheduleItemUpdateRequest,
) -> ScheduleItemRead:
    item = require_schedule_item(state, trip_id, item_id)
    trip = require_trip(state, trip_id)
    date_value = required_patch_value(
        payload,
        "date",
        payload.date,
        item.date,
    )
    start_time = required_patch_value(
        payload,
        "start_time",
        payload.start_time,
        item.start_time,
    )
    end_time = required_patch_value(
        payload,
        "end_time",
        payload.end_time,
        item.end_time,
    )
    _validate_schedule_values(
        trip.start_date,
        trip.end_date,
        date_value,
        start_time,
        end_time,
    )
    place_id = nullable_patch_value(
        payload,
        "place_id",
        payload.place_id,
        item.place_id,
    )
    if place_id is not None:
        _ = require_wanted_place(state, trip_id, place_id)
    updated = ScheduleItemRead(
        id=item.id,
        trip_id=item.trip_id,
        name=required_patch_value(payload, "name", payload.name, item.name),
        date=date_value,
        start_time=start_time,
        end_time=end_time,
        place_id=place_id,
        notes=nullable_patch_value(
            payload,
            "notes",
            payload.notes,
            item.notes,
        ),
        source=required_patch_value(
            payload,
            "source",
            payload.source,
            item.source,
        ),
    )
    state.schedule_items[item.id] = updated
    return updated


@synchronized
def delete_schedule_item(state: AppState, trip_id: str, item_id: str) -> None:
    _ = require_schedule_item(state, trip_id, item_id)
    del state.schedule_items[item_id]


@synchronized
def schedule_for_date(
    state: AppState,
    trip_id: str,
    target_date: date,
) -> ScheduleResponse:
    schedule = list_schedule(state, trip_id)
    items = [item for item in schedule.items if item.date == target_date]
    return ScheduleResponse(trip_id=trip_id, items=items)


@synchronized
def validate_schedule_item(
    state: AppState,
    trip_id: str,
    payload: ScheduleItemCreateRequest,
) -> None:
    trip = require_trip(state, trip_id)
    _validate_schedule_values(
        trip.start_date,
        trip.end_date,
        payload.date,
        payload.start_time,
        payload.end_time,
    )
    if payload.place_id is not None:
        _ = require_wanted_place(state, trip_id, payload.place_id)


def _validate_schedule_values(
    trip_start: date,
    trip_end: date,
    item_date: date,
    start_time: time,
    end_time: time,
) -> None:
    if not trip_start <= item_date <= trip_end:
        raise DomainValidationError(SCHEDULE_DATE_ERROR)
    if start_time.tzinfo is not None or end_time.tzinfo is not None:
        raise DomainValidationError(SCHEDULE_TIMEZONE_ERROR)
    if end_time <= start_time:
        raise DomainValidationError(SCHEDULE_TIME_ERROR)
