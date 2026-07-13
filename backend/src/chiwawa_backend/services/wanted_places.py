from chiwawa_backend.schemas.base import PlaceSource
from chiwawa_backend.schemas.places import (
    WantedPlaceCreateRequest,
    WantedPlaceListResponse,
    WantedPlaceRead,
    WantedPlaceUpdateRequest,
)
from chiwawa_backend.services.common import require_trip, require_wanted_place
from chiwawa_backend.state import AppState, synchronized


@synchronized
def create_wanted_place(
    state: AppState,
    trip_id: str,
    payload: WantedPlaceCreateRequest,
    source: PlaceSource = PlaceSource.MANUAL,
) -> WantedPlaceRead:
    trip = require_trip(state, trip_id)
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
    updated = WantedPlaceRead(
        id=place.id,
        trip_id=place.trip_id,
        name=payload.name or place.name,
        city=payload.city or place.city,
        country=payload.country or place.country,
        latitude=payload.latitude if payload.latitude is not None else place.latitude,
        longitude=payload.longitude
        if payload.longitude is not None
        else place.longitude,
        priority=payload.priority or place.priority,
        notes=payload.notes if payload.notes is not None else place.notes,
        source=place.source,
    )
    state.wanted_places[place.id] = updated
    return updated


@synchronized
def delete_wanted_place(state: AppState, trip_id: str, place_id: str) -> None:
    _ = require_wanted_place(state, trip_id, place_id)
    del state.wanted_places[place_id]
