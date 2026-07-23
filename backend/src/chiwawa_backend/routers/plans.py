from typing import Annotated

from fastapi import APIRouter, Depends, status

from chiwawa_backend.dependencies import get_state, require_user_id_when_enabled
from chiwawa_backend.schemas.plans import (
    AIPlanCreateRequest,
    PlanConfirmResponse,
    PlanDraftRead,
    PlanJobRead,
    RouteOptimizationRequest,
    RouteOptimizationResponse,
)
from chiwawa_backend.services import plans as plan_service
from chiwawa_backend.state import AppState

router = APIRouter(
    prefix="/api/v1/trips/{trip_id}",
    tags=["plans"],
    dependencies=[Depends(require_user_id_when_enabled)],
)
StateDep = Annotated[AppState, Depends(get_state)]


@router.post(
    "/ai-plans",
    status_code=status.HTTP_202_ACCEPTED,
)
def create_ai_plan(
    trip_id: str,
    payload: AIPlanCreateRequest,
    state: StateDep,
) -> PlanJobRead:
    return plan_service.create_plan_job(state, trip_id, payload)


@router.get("/ai-plans/{plan_job_id}")
def get_ai_plan_status(
    trip_id: str,
    plan_job_id: str,
    state: StateDep,
) -> PlanJobRead:
    return plan_service.get_plan_job(state, trip_id, plan_job_id)


@router.get("/plans/{plan_id}")
def get_plan(trip_id: str, plan_id: str, state: StateDep) -> PlanDraftRead:
    return plan_service.get_plan(state, trip_id, plan_id)


@router.post(
    "/plans/{plan_id}/confirm",
    status_code=status.HTTP_201_CREATED,
)
def confirm_plan(
    trip_id: str,
    plan_id: str,
    state: StateDep,
) -> PlanConfirmResponse:
    return plan_service.confirm_plan(state, trip_id, plan_id)


@router.post(
    "/route-optimizations",
    status_code=status.HTTP_201_CREATED,
)
def optimize_route(
    trip_id: str,
    payload: RouteOptimizationRequest,
    state: StateDep,
) -> RouteOptimizationResponse:
    return plan_service.optimize_route(state, trip_id, payload)
