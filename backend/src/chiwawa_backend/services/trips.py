from __future__ import annotations

from typing import TYPE_CHECKING

from chiwawa_backend.errors import DomainValidationError
from chiwawa_backend.schemas.trips import (
    MAX_TRIP_DAYS,
    TripCreateRequest,
    TripListResponse,
    TripRead,
    TripUpdateRequest,
)
from chiwawa_backend.services.common import require_trip
from chiwawa_backend.state import AppState, synchronized

if TYPE_CHECKING:
    from datetime import date

    from chiwawa_backend.schemas.plans import PlanDraftRead

TRIP_DATE_ORDER_ERROR = "end_date must not be before start_date"
TRIP_RESOURCE_RANGE_ERROR = "trip dates must include existing dated resources"
TRIP_DURATION_ERROR = f"trip duration must not exceed {MAX_TRIP_DAYS} days"


@synchronized
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


@synchronized
def list_trips(state: AppState) -> TripListResponse:
    return TripListResponse(items=list(state.trips.values()))


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
    start_date = (
        payload.start_date if payload.start_date is not None else trip.start_date
    )
    end_date = payload.end_date if payload.end_date is not None else trip.end_date
    if end_date < start_date:
        raise DomainValidationError(TRIP_DATE_ORDER_ERROR)
    if (end_date - start_date).days >= MAX_TRIP_DAYS:
        raise DomainValidationError(TRIP_DURATION_ERROR)
    if _has_dated_resource_outside(state, trip_id, start_date, end_date):
        raise DomainValidationError(TRIP_RESOURCE_RANGE_ERROR)
    _discard_plan_drafts_outside(state, trip_id, start_date, end_date)
    updated = TripRead(
        id=trip.id,
        title=payload.title if payload.title is not None else trip.title,
        city=payload.city if payload.city is not None else trip.city,
        country=payload.country if payload.country is not None else trip.country,
        start_date=start_date,
        end_date=end_date,
        travelers=payload.travelers
        if payload.travelers is not None
        else trip.travelers,
        interests=payload.interests
        if payload.interests is not None
        else trip.interests,
        travel_style=payload.travel_style
        if payload.travel_style is not None
        else trip.travel_style,
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
    for plan_id in plan_ids:
        _ = state.confirmed_plan_items.pop(plan_id, None)
        _ = state.replan_source_items.pop(plan_id, None)
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
    # 미확정 plan draft는 실제 리소스가 아니므로 날짜 변경을 막는 근거에서 제외한다.
    dated_resources = [
        item.date for item in state.schedule_items.values() if item.trip_id == trip_id
    ]
    dated_resources.extend(
        item.date for item in state.recommendations.values() if item.trip_id == trip_id
    )
    return any(not start_date <= item_date <= end_date for item_date in dated_resources)


def _discard_plan_drafts_outside(
    state: AppState,
    trip_id: str,
    start_date: date,
    end_date: date,
) -> None:
    # 새 기간 밖으로 벗어나는 미확정 draft는 확정할 수 없으므로 폐기한다.
    draft_ids = [
        plan.id
        for plan in state.plans.values()
        if plan.trip_id == trip_id
        and plan.id not in state.confirmed_plans
        and _plan_has_date_outside(plan, start_date, end_date)
    ]
    for plan_id in draft_ids:
        del state.plans[plan_id]
        _ = state.replan_source_items.pop(plan_id, None)


def _plan_has_date_outside(
    plan: PlanDraftRead,
    start_date: date,
    end_date: date,
) -> bool:
    plan_dates = [day.date for day in plan.days]
    plan_dates.extend(stop.date for day in plan.days for stop in day.stops)
    return any(not start_date <= plan_date <= end_date for plan_date in plan_dates)
