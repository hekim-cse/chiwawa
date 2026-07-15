from datetime import date

from chiwawa_backend.errors import DomainValidationError
from chiwawa_backend.schemas.trips import (
    MAX_TRIP_DAYS,
    TripCreateRequest,
    TripListResponse,
    TripRead,
    TripUpdateRequest,
)
from chiwawa_backend.services.common import require_trip
from chiwawa_backend.services.patch_values import required_patch_value
from chiwawa_backend.state import AppState, synchronized

TRIP_DATE_ORDER_ERROR = "end_date must not be before start_date"
TRIP_RESOURCE_RANGE_ERROR = "trip dates must include existing dated resources"
TRIP_DURATION_ERROR = f"trip duration must not exceed {MAX_TRIP_DAYS} days"


@synchronized
def create_trip(
    state: AppState,
    payload: TripCreateRequest,
    actor_id: int = 0,
) -> TripRead:
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
    state.trip_owners[trip.id] = actor_id
    return trip


@synchronized
def list_trips(
    state: AppState,
    actor_id: int = 0,
    *,
    include_unowned: bool = True,
) -> TripListResponse:
    items = [
        trip
        for trip_id, trip in state.trips.items()
        if state.trip_owners.get(trip_id) == actor_id
        or (trip_id not in state.trip_owners and include_unowned)
    ]
    return TripListResponse(items=items)


@synchronized
def get_trip(state: AppState, trip_id: str) -> TripRead:
    return require_trip(state, trip_id)


@synchronized
def update_trip(
    state: AppState,
    trip_id: str,
    payload: TripUpdateRequest,
) -> TripRead:
    trip = require_trip(state, trip_id)
    start_date = required_patch_value(
        payload,
        "start_date",
        payload.start_date,
        trip.start_date,
    )
    end_date = required_patch_value(
        payload,
        "end_date",
        payload.end_date,
        trip.end_date,
    )
    if end_date < start_date:
        raise DomainValidationError(TRIP_DATE_ORDER_ERROR)
    if (end_date - start_date).days >= MAX_TRIP_DAYS:
        raise DomainValidationError(TRIP_DURATION_ERROR)
    if _has_dated_resource_outside(state, trip_id, start_date, end_date):
        raise DomainValidationError(TRIP_RESOURCE_RANGE_ERROR)
    updated = TripRead(
        id=trip.id,
        title=required_patch_value(payload, "title", payload.title, trip.title),
        city=required_patch_value(payload, "city", payload.city, trip.city),
        country=required_patch_value(
            payload,
            "country",
            payload.country,
            trip.country,
        ),
        start_date=start_date,
        end_date=end_date,
        travelers=required_patch_value(
            payload,
            "travelers",
            payload.travelers,
            trip.travelers,
        ),
        interests=required_patch_value(
            payload,
            "interests",
            payload.interests,
            trip.interests,
        ),
        travel_style=required_patch_value(
            payload,
            "travel_style",
            payload.travel_style,
            trip.travel_style,
        ),
    )
    state.trips[trip_id] = updated
    return updated


@synchronized
def delete_trip(state: AppState, trip_id: str) -> None:
    _ = require_trip(state, trip_id)
    plan_ids = {plan.id for plan in state.plans.values() if plan.trip_id == trip_id}
    recommendation_ids = {
        item.id for item in state.recommendations.values() if item.trip_id == trip_id
    }
    del state.trips[trip_id]
    _ = state.trip_owners.pop(trip_id, None)
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
    state.confirmed_plans.difference_update(plan_ids)
    for candidate_id in [
        key
        for key, confirmation in state.confirmed_photo_places.items()
        if confirmation.wanted_place.trip_id == trip_id
    ]:
        del state.confirmed_photo_places[candidate_id]
    for recommendation_id in recommendation_ids:
        _ = state.added_recommendations.pop(recommendation_id, None)


def _has_dated_resource_outside(
    state: AppState,
    trip_id: str,
    start_date: date,
    end_date: date,
) -> bool:
    dated_resources = [
        item.date for item in state.schedule_items.values() if item.trip_id == trip_id
    ]
    dated_resources.extend(
        item.date for item in state.recommendations.values() if item.trip_id == trip_id
    )
    dated_resources.extend(
        day.date
        for plan in state.plans.values()
        if plan.trip_id == trip_id
        for day in plan.days
    )
    dated_resources.extend(
        stop.date
        for plan in state.plans.values()
        if plan.trip_id == trip_id
        for day in plan.days
        for stop in day.stops
    )
    return any(not start_date <= item_date <= end_date for item_date in dated_resources)
