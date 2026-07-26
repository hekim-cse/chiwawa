from typing import Annotated

from fastapi import APIRouter, Depends, status

from chiwawa_backend.dependencies import (
    get_route_planner,
    get_state,
    get_time_zone_provider,
)
from chiwawa_backend.errors import DomainValidationError
from chiwawa_backend.schemas.plans import (
    AIPlanCreateRequest,
    PlanConfirmResponse,
    PlanDraftRead,
    PlanJobRead,
    RouteOptimizationConfirmRequest,
    RouteOptimizationRequest,
    RouteOptimizationResponse,
)
from chiwawa_backend.schemas.schedule import ScheduleResponse
from chiwawa_backend.services import plans as plan_service
from chiwawa_backend.services.route_optimization import (
    MISSING_ENDPOINTS_MESSAGE,
    RoutePlanner,
    build_modal_request,
    route_optimization_date,
    to_route_optimization_response,
)
from chiwawa_backend.services.route_optimization import (
    confirm_route_optimization as confirm_optimized_route,
)
from chiwawa_backend.services.time_zone import TimeZoneProvider
from chiwawa_backend.state import AppState

router = APIRouter(prefix="/api/v1/trips/{trip_id}", tags=["plans"])
StateDep = Annotated[AppState, Depends(get_state)]
RoutePlannerDep = Annotated[RoutePlanner, Depends(get_route_planner)]
TimeZoneProviderDep = Annotated[TimeZoneProvider, Depends(get_time_zone_provider)]


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
async def optimize_route(
    trip_id: str,
    payload: RouteOptimizationRequest,
    state: StateDep,
    route_planner: RoutePlannerDep,
    time_zone_provider: TimeZoneProviderDep,
) -> RouteOptimizationResponse:
    if payload.start is None:
        raise DomainValidationError(MISSING_ENDPOINTS_MESSAGE)
    date = route_optimization_date(state, trip_id, payload)
    timezone = await time_zone_provider.resolve(
        latitude=payload.start.lat,
        longitude=payload.start.lng,
        date=date,
    )
    request = build_modal_request(state, trip_id, payload, timezone=timezone)
    planning = await route_planner.plan_trip(
        request,
        include_recommendations=payload.include_recommendations,
    )
    response = to_route_optimization_response(planning, payload)
    if response.timeline is not None:
        with state.lock:
            route_key = (trip_id, payload.day_index)
            state.issued_route_timelines[route_key] = response.timeline
            state.issued_route_recommendations[route_key] = (
                response.recommendation_groups
            )
    return response


@router.post("/route-optimizations/confirm")
def confirm_route_optimization(
    trip_id: str,
    payload: RouteOptimizationConfirmRequest,
    state: StateDep,
) -> ScheduleResponse:
    return confirm_optimized_route(state, trip_id, payload)
