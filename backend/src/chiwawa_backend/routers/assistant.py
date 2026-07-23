from typing import Annotated

from fastapi import APIRouter, Depends, status

from chiwawa_backend.dependencies import get_state, require_user_id_when_enabled
from chiwawa_backend.schemas.travel import (
    NearbyRecommendationRequest,
    NearbyRecommendationResponse,
    ReplanRequest,
    ReplanResponse,
)
from chiwawa_backend.services import travel as travel_service
from chiwawa_backend.state import AppState

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}/assistant",
    tags=["assistant"],
    dependencies=[Depends(require_user_id_when_enabled)],
)
StateDep = Annotated[AppState, Depends(get_state)]


@router.post(
    "/nearby",
    status_code=status.HTTP_201_CREATED,
)
def nearby_recommendations(
    trip_id: str,
    payload: NearbyRecommendationRequest,
    state: StateDep,
) -> NearbyRecommendationResponse:
    return travel_service.nearby_recommendations(state, trip_id, payload)


@router.post(
    "/replan",
    status_code=status.HTTP_201_CREATED,
)
def replan_trip(
    trip_id: str,
    payload: ReplanRequest,
    state: StateDep,
) -> ReplanResponse:
    return travel_service.replan_trip(state, trip_id, payload)
