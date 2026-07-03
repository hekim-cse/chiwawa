from typing import Annotated

from fastapi import APIRouter, Depends, status

from chiwawa_backend.dependencies import get_state
from chiwawa_backend.schemas.travel import (
    AddRecommendationResponse,
    FreeTimeRecommendationRequest,
    FreeTimeRecommendationResponse,
    TodayScheduleResponse,
)
from chiwawa_backend.services import travel as travel_service
from chiwawa_backend.state import AppState

router = APIRouter(prefix="/api/v1/trips/{trip_id}/travel", tags=["travel"])
StateDep = Annotated[AppState, Depends(get_state)]


@router.get("/today")
def today_schedule(trip_id: str, state: StateDep) -> TodayScheduleResponse:
    return travel_service.today_schedule(state, trip_id)


@router.post(
    "/free-time-recommendations",
    status_code=status.HTTP_201_CREATED,
)
def recommend_free_time(
    trip_id: str,
    payload: FreeTimeRecommendationRequest,
    state: StateDep,
) -> FreeTimeRecommendationResponse:
    return travel_service.recommend_free_time(state, trip_id, payload)


@router.post(
    "/free-time-recommendations/{recommendation_id}/add",
    status_code=status.HTTP_201_CREATED,
)
def add_recommendation(
    trip_id: str,
    recommendation_id: str,
    state: StateDep,
) -> AddRecommendationResponse:
    return travel_service.add_recommendation_to_schedule(
        state,
        trip_id,
        recommendation_id,
    )
