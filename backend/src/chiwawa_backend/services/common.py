from chiwawa_backend.errors import NotFoundError
from chiwawa_backend.schemas.memorial import MemorialRecordRead
from chiwawa_backend.schemas.places import (
    PhotoPlaceSearchResponse,
    WantedPlaceRead,
)
from chiwawa_backend.schemas.plans import PlanDraftRead, PlanJobRead
from chiwawa_backend.schemas.schedule import ScheduleItemRead
from chiwawa_backend.schemas.travel import FreeTimeRecommendationRead
from chiwawa_backend.schemas.trips import TripRead
from chiwawa_backend.state import AppState


def require_trip(state: AppState, trip_id: str) -> TripRead:
    try:
        return state.trips[trip_id]
    except KeyError as error:
        raise NotFoundError(entity="trip", entity_id=trip_id) from error


def require_photo_search(
    state: AppState,
    trip_id: str,
    search_id: str,
) -> PhotoPlaceSearchResponse:
    search = state.photo_searches.get(search_id)
    if search is None or search.trip_id != trip_id:
        raise NotFoundError(entity="photo_search", entity_id=search_id)
    return search


def require_wanted_place(
    state: AppState,
    trip_id: str,
    place_id: str,
) -> WantedPlaceRead:
    place = state.wanted_places.get(place_id)
    if place is None or place.trip_id != trip_id:
        raise NotFoundError(entity="wanted_place", entity_id=place_id)
    return place


def require_plan_job(state: AppState, trip_id: str, job_id: str) -> PlanJobRead:
    job = state.plan_jobs.get(job_id)
    if job is None or job.trip_id != trip_id:
        raise NotFoundError(entity="plan_job", entity_id=job_id)
    return job


def require_plan(state: AppState, trip_id: str, plan_id: str) -> PlanDraftRead:
    plan = state.plans.get(plan_id)
    if plan is None or plan.trip_id != trip_id:
        raise NotFoundError(entity="plan", entity_id=plan_id)
    return plan


def require_schedule_item(
    state: AppState,
    trip_id: str,
    item_id: str,
) -> ScheduleItemRead:
    item = state.schedule_items.get(item_id)
    if item is None or item.trip_id != trip_id:
        raise NotFoundError(entity="schedule_item", entity_id=item_id)
    return item


def require_recommendation(
    state: AppState,
    trip_id: str,
    recommendation_id: str,
) -> FreeTimeRecommendationRead:
    recommendation = state.recommendations.get(recommendation_id)
    if recommendation is None or recommendation.trip_id != trip_id:
        raise NotFoundError(entity="recommendation", entity_id=recommendation_id)
    return recommendation


def require_memorial(
    state: AppState,
    trip_id: str,
) -> MemorialRecordRead:
    memorial = state.memorials.get(trip_id)
    if memorial is None:
        raise NotFoundError(entity="memorial", entity_id=trip_id)
    return memorial
