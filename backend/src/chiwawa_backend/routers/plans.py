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
    ConfirmedRouteOptimizationsResponse,
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
    list_confirmed_route_optimizations,
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
            start = payload.start
            end = payload.end
            if start is None or end is None:
                raise DomainValidationError(MISSING_ENDPOINTS_MESSAGE)

            #state.issued_route_endpoints[route_key] = (start, end)
            state.issued_route_endpoints[route_key] = (payload.start, payload.end)
            state.issued_route_responses[route_key] = response
            day_plan = next(
                day for day in planning.day_plans if day.day_index == payload.day_index
            )
            requested_mode = response.timeline.travel_mode
            state.issued_route_options[route_key] = next(
                option
                for option in day_plan.route_options
                if option.travel_mode == requested_mode
            )
            state.issued_route_timezones[route_key] = timezone
    return response


@router.get("/route-optimizations/confirmed")
def get_confirmed_route_optimizations(
    trip_id: str,
    state: StateDep,
) -> ConfirmedRouteOptimizationsResponse:
    return list_confirmed_route_optimizations(state, trip_id)


@router.post("/route-optimizations/confirm")
def confirm_route_optimization(
    trip_id: str,
    payload: RouteOptimizationConfirmRequest,
    state: StateDep,
) -> ScheduleResponse:
    return confirm_optimized_route(state, trip_id, payload)
