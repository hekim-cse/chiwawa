from chiwawa_backend.schemas.base import PlaceSource
from chiwawa_backend.schemas.places import (
    WantedPlaceCreateRequest,
    WantedPlaceListResponse,
    WantedPlaceRead,
    WantedPlaceUpdateRequest,
)
from chiwawa_backend.services.common import require_trip, require_wanted_place
from chiwawa_backend.services.coordinates import (
    require_coordinate_pair,
    require_coordinate_patch,
)
from chiwawa_backend.services.patch_values import (
    nullable_patch_value,
    required_patch_value,
)
from chiwawa_backend.state import AppState, synchronized


@synchronized
def create_wanted_place(
    state: AppState,
    trip_id: str,
    payload: WantedPlaceCreateRequest,
    source: PlaceSource = PlaceSource.MANUAL,
) -> WantedPlaceRead:
    trip = require_trip(state, trip_id)
    require_coordinate_pair(payload.latitude, payload.longitude)
    place = WantedPlaceRead(
        id=state.next_id("place"),
        trip_id=trip_id,
        name=payload.name,
        city=payload.city or trip.city,
        country=payload.country,
        latitude=payload.latitude,
        longitude=payload.longitude,
        priority=payload.priority,
        notes=payload.notes,
        source=source,
    )
    state.wanted_places[place.id] = place
    return place


@synchronized
def list_wanted_places(state: AppState, trip_id: str) -> WantedPlaceListResponse:
    _ = require_trip(state, trip_id)
    items = [
        place for place in state.wanted_places.values() if place.trip_id == trip_id
    ]
    return WantedPlaceListResponse(items=items)


@synchronized
def update_wanted_place(
    state: AppState,
    trip_id: str,
    place_id: str,
    payload: WantedPlaceUpdateRequest,
) -> WantedPlaceRead:
    place = require_wanted_place(state, trip_id, place_id)
    require_coordinate_patch(
        payload.model_fields_set,
        payload.latitude,
        payload.longitude,
    )
    updated = WantedPlaceRead(
        id=place.id,
        trip_id=place.trip_id,
        name=required_patch_value(payload, "name", payload.name, place.name),
        city=required_patch_value(payload, "city", payload.city, place.city),
        country=required_patch_value(
            payload,
            "country",
            payload.country,
            place.country,
        ),
        latitude=nullable_patch_value(
            payload,
            "latitude",
            payload.latitude,
            place.latitude,
        ),
        longitude=nullable_patch_value(
            payload,
            "longitude",
            payload.longitude,
            place.longitude,
        ),
        priority=required_patch_value(
            payload,
            "priority",
            payload.priority,
            place.priority,
        ),
        notes=nullable_patch_value(
            payload,
            "notes",
            payload.notes,
            place.notes,
        ),
        source=place.source,
    )
    require_coordinate_pair(updated.latitude, updated.longitude)
    state.wanted_places[place.id] = updated
    return updated


@synchronized
def delete_wanted_place(state: AppState, trip_id: str, place_id: str) -> None:
    _ = require_wanted_place(state, trip_id, place_id)
    del state.wanted_places[place_id]
    _clear_schedule_references(state, place_id)
    _clear_plan_references(state, place_id)
    for candidate_id in [
        key
        for key, confirmation in state.confirmed_photo_places.items()
        if confirmation.wanted_place.id == place_id
    ]:
        del state.confirmed_photo_places[candidate_id]


def _clear_schedule_references(state: AppState, place_id: str) -> None:
    for item_id, item in state.schedule_items.items():
        if item.place_id == place_id:
            state.schedule_items[item_id] = item.model_copy(
                update={"place_id": None},
            )


def _clear_plan_references(
    state: AppState,
    place_id: str,
) -> None:
    for plan_id, plan in state.plans.items():
        days = [
            day.model_copy(
                update={
                    "stops": [
                        stop.model_copy(update={"place_id": None})
                        if stop.place_id == place_id
                        else stop
                        for stop in day.stops
                    ],
                },
            )
            for day in plan.days
        ]
        state.plans[plan_id] = plan.model_copy(update={"days": days})
