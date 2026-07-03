from chiwawa_backend.schemas.trips import (
    TripCreateRequest,
    TripListResponse,
    TripRead,
    TripUpdateRequest,
)
from chiwawa_backend.services.common import require_trip
from chiwawa_backend.state import AppState


def create_trip(state: AppState, payload: TripCreateRequest) -> TripRead:
    trip_id = state.next_id("trip")
    title = payload.title or f"{payload.city} travel"
    trip = TripRead(
        id=trip_id,
        title=title,
        city=payload.city,
        country=payload.country,
        start_date=payload.start_date,
        end_date=payload.end_date,
        travelers=payload.travelers,
        interests=payload.interests,
        travel_style=payload.travel_style,
    )
    state.trips[trip.id] = trip
    return trip


def list_trips(state: AppState) -> TripListResponse:
    return TripListResponse(items=list(state.trips.values()))


def get_trip(state: AppState, trip_id: str) -> TripRead:
    return require_trip(state, trip_id)


def update_trip(
    state: AppState,
    trip_id: str,
    payload: TripUpdateRequest,
) -> TripRead:
    trip = require_trip(state, trip_id)
    start_date = payload.start_date or trip.start_date
    end_date = payload.end_date or trip.end_date
    if end_date < start_date:
        start_date = trip.start_date
        end_date = trip.end_date
    updated = TripRead(
        id=trip.id,
        title=payload.title or trip.title,
        city=payload.city or trip.city,
        country=payload.country or trip.country,
        start_date=start_date,
        end_date=end_date,
        travelers=payload.travelers or trip.travelers,
        interests=payload.interests
        if payload.interests is not None
        else trip.interests,
        travel_style=payload.travel_style or trip.travel_style,
    )
    state.trips[trip_id] = updated
    return updated


def delete_trip(state: AppState, trip_id: str) -> None:
    _ = require_trip(state, trip_id)
    del state.trips[trip_id]
    for collection in (
        state.photo_searches,
        state.wanted_places,
        state.plan_jobs,
        state.plans,
        state.schedule_items,
        state.recommendations,
        state.photos,
    ):
        for item_id in [
            key
            for key, item in collection.items()
            if getattr(item, "trip_id", None) == trip_id
        ]:
            del collection[item_id]
    _ = state.memorials.pop(trip_id, None)
