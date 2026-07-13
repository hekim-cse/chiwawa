from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from chiwawa_backend.errors import DomainValidationError
from chiwawa_backend.schemas.base import PlaceSource
from chiwawa_backend.schemas.schedule import ScheduleItemCreateRequest
from chiwawa_backend.schemas.travel import (
    AddRecommendationResponse,
    FreeTimeRecommendationRead,
    FreeTimeRecommendationRequest,
    FreeTimeRecommendationResponse,
    NearbyRecommendationRead,
    NearbyRecommendationRequest,
    NearbyRecommendationResponse,
    ReplanRequest,
    ReplanResponse,
    TodayScheduleResponse,
)
from chiwawa_backend.services.common import require_recommendation, require_trip
from chiwawa_backend.services.plans import build_replan_from_schedule
from chiwawa_backend.services.schedule import create_schedule_item, schedule_for_date
from chiwawa_backend.state import AppState, synchronized

RECOMMENDATION_DATE_ERROR = "recommendation date must be within trip dates"


@synchronized
def today_schedule(state: AppState, trip_id: str) -> TodayScheduleResponse:
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    return TodayScheduleResponse(
        trip_id=trip_id,
        date=today,
        schedule=schedule_for_date(state, trip_id, today),
    )


@synchronized
def recommend_free_time(
    state: AppState,
    trip_id: str,
    payload: FreeTimeRecommendationRequest,
) -> FreeTimeRecommendationResponse:
    trip = require_trip(state, trip_id)
    if not trip.start_date <= payload.date <= trip.end_date:
        raise DomainValidationError(RECOMMENDATION_DATE_ERROR)
    area = payload.current_area or trip.city
    duration = int(
        (
            datetime.combine(payload.date, payload.end_time)
            - datetime.combine(payload.date, payload.start_time)
        ).total_seconds()
        // 60,
    )
    recommended_duration = min(60, duration)
    recommended_end = (
        datetime.combine(payload.date, payload.start_time)
        + timedelta(minutes=recommended_duration)
    ).time()
    item = FreeTimeRecommendationRead(
        id=state.next_id("recommendation"),
        trip_id=trip_id,
        title=f"{area} short activity",
        place_name=f"{area} neighborhood walk",
        duration_minutes=recommended_duration,
        reason="Fits the open time window and nearby travel context.",
        date=payload.date,
        start_time=payload.start_time,
        end_time=recommended_end,
    )
    state.recommendations[item.id] = item
    return FreeTimeRecommendationResponse(trip_id=trip_id, items=[item])


@synchronized
def add_recommendation_to_schedule(
    state: AppState,
    trip_id: str,
    recommendation_id: str,
) -> AddRecommendationResponse:
    recommendation = require_recommendation(state, trip_id, recommendation_id)
    existing_item_id = state.added_recommendations.get(recommendation_id)
    if existing_item_id is not None:
        existing_item = state.schedule_items.get(existing_item_id)
        if existing_item is not None and existing_item.trip_id == trip_id:
            return AddRecommendationResponse(schedule_item=existing_item)
    schedule_item = create_schedule_item(
        state,
        trip_id,
        ScheduleItemCreateRequest(
            name=recommendation.place_name,
            date=recommendation.date,
            start_time=recommendation.start_time,
            end_time=recommendation.end_time,
            notes=recommendation.reason,
            source=PlaceSource.RECOMMENDATION,
        ),
    )
    state.added_recommendations[recommendation_id] = schedule_item.id
    return AddRecommendationResponse(schedule_item=schedule_item)


@synchronized
def nearby_recommendations(
    state: AppState,
    trip_id: str,
    payload: NearbyRecommendationRequest,
) -> NearbyRecommendationResponse:
    trip = require_trip(state, trip_id)
    theme = payload.theme or "local"
    items = [
        NearbyRecommendationRead(
            title=f"{theme.title()} stop near current location",
            place_name=f"{trip.city} nearby {theme}",
            estimated_walk_minutes=8,
            reason="Close enough to add without disrupting the current route.",
        ),
        NearbyRecommendationRead(
            title="Quick photo detour",
            place_name=f"{trip.city} side-street viewpoint",
            estimated_walk_minutes=12,
            reason="Matches the photo-centered travel goal.",
        ),
    ]
    return NearbyRecommendationResponse(trip_id=trip_id, items=items)


@synchronized
def replan_trip(
    state: AppState,
    trip_id: str,
    payload: ReplanRequest,
) -> ReplanResponse:
    plan = build_replan_from_schedule(
        state,
        trip_id,
        payload.delay_minutes,
        payload.current_item_id,
    )
    reason = payload.reason or "schedule update"
    generated_at = datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
    message = f"Replanned for {reason} at {generated_at}"
    return ReplanResponse(plan=plan, message=message)
