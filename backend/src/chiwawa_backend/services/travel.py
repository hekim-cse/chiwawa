from datetime import UTC, datetime

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
from chiwawa_backend.state import AppState


def today_schedule(state: AppState, trip_id: str) -> TodayScheduleResponse:
    today = datetime.now(UTC).date()
    return TodayScheduleResponse(
        trip_id=trip_id,
        date=today,
        schedule=schedule_for_date(state, trip_id, today),
    )


def recommend_free_time(
    state: AppState,
    trip_id: str,
    payload: FreeTimeRecommendationRequest,
) -> FreeTimeRecommendationResponse:
    trip = require_trip(state, trip_id)
    area = payload.current_area or trip.city
    item = FreeTimeRecommendationRead(
        id=state.next_id("recommendation"),
        trip_id=trip_id,
        title=f"{area} short activity",
        place_name=f"{area} neighborhood walk",
        duration_minutes=60,
        reason="Fits the open time window and nearby travel context.",
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    state.recommendations[item.id] = item
    return FreeTimeRecommendationResponse(trip_id=trip_id, items=[item])


def add_recommendation_to_schedule(
    state: AppState,
    trip_id: str,
    recommendation_id: str,
) -> AddRecommendationResponse:
    recommendation = require_recommendation(state, trip_id, recommendation_id)
    schedule_item = create_schedule_item(
        state=state,
        trip_id=trip_id,
        payload=ScheduleItemCreateRequest(
            name=recommendation.place_name,
            date=recommendation.date,
            start_time=recommendation.start_time,
            end_time=recommendation.end_time,
            notes=recommendation.reason,
            source=PlaceSource.RECOMMENDATION,
        ),
    )
    return AddRecommendationResponse(schedule_item=schedule_item)


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


def replan_trip(
    state: AppState,
    trip_id: str,
    payload: ReplanRequest,
) -> ReplanResponse:
    plan = build_replan_from_schedule(state, trip_id, payload.delay_minutes)
    reason = payload.reason or "schedule update"
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    message = f"Replanned for {reason} at {generated_at}"
    return ReplanResponse(plan=plan, message=message)
