from __future__ import annotations

from typing import TYPE_CHECKING

from chiwawa_backend.errors import DomainValidationError
from chiwawa_backend.schemas.base import PlaceSource, PlanJobStatus
from chiwawa_backend.schemas.plans import (
    AIPlanCreateRequest,
    PlanConfirmResponse,
    PlanDayRead,
    PlanDraftRead,
    PlanJobRead,
    PlanStopRead,
    RouteOptimizationRequest,
    RouteOptimizationResponse,
    RouteStopRead,
)
from chiwawa_backend.schemas.schedule import ScheduleItemCreateRequest
from chiwawa_backend.services.common import (
    require_plan,
    require_plan_job,
    require_schedule_item,
    require_trip,
)
from chiwawa_backend.services.plan_builder import (
    PlanBuildOptions,
    build_plan,
    shift_datetime,
)
from chiwawa_backend.services.schedule import (
    create_schedule_item,
    list_schedule,
    validate_schedule_item,
)
from chiwawa_backend.state import synchronized

if TYPE_CHECKING:
    from datetime import date

    from chiwawa_backend.state import AppState

REPLAN_RANGE_ERROR = "replanned schedule must remain within trip dates"
REPLAN_DAY_ERROR = "replanned schedule items must start and end on the same date"


@synchronized
def create_plan_job(
    state: AppState,
    trip_id: str,
    payload: AIPlanCreateRequest,
) -> PlanJobRead:
    trip = require_trip(state, trip_id)
    options = PlanBuildOptions(
        title=f"{trip.title} AI draft",
        start_time=payload.preferred_start_time,
        end_time=payload.preferred_end_time,
        pace=payload.pace or trip.travel_style,
    )
    plan = build_plan(state, trip_id, options)
    state.plans[plan.id] = plan
    job = PlanJobRead(
        id=state.next_id("plan_job"),
        trip_id=trip_id,
        status=PlanJobStatus.COMPLETED,
        plan_id=plan.id,
        message="Plan draft generated from wanted places and photo confirmations.",
    )
    state.plan_jobs[job.id] = job
    return job


@synchronized
def get_plan_job(state: AppState, trip_id: str, job_id: str) -> PlanJobRead:
    return require_plan_job(state, trip_id, job_id)


@synchronized
def get_plan(state: AppState, trip_id: str, plan_id: str) -> PlanDraftRead:
    return require_plan(state, trip_id, plan_id)


@synchronized
def confirm_plan(state: AppState, trip_id: str, plan_id: str) -> PlanConfirmResponse:
    plan = require_plan(state, trip_id, plan_id)
    if plan_id not in state.confirmed_plans:
        payloads = [
            ScheduleItemCreateRequest(
                name=stop.name,
                date=stop.date,
                start_time=stop.start_time,
                end_time=stop.end_time,
                place_id=stop.place_id,
                notes=stop.notes,
                source=PlaceSource.PLAN,
            )
            for day in plan.days
            for stop in day.stops
        ]
        for payload in payloads:
            validate_schedule_item(state, trip_id, payload)
        for payload in payloads:
            _ = create_schedule_item(state, trip_id, payload)
        state.confirmed_plans.add(plan_id)
    schedule = list_schedule(state, trip_id)
    return PlanConfirmResponse(plan=plan, schedule=schedule)


@synchronized
def optimize_route(
    state: AppState,
    trip_id: str,
    payload: RouteOptimizationRequest,
) -> RouteOptimizationResponse:
    _ = require_trip(state, trip_id)
    places = [
        place for place in state.wanted_places.values() if place.trip_id == trip_id
    ]
    ordered = sorted(places, key=lambda place: (-place.priority, place.name))
    route_stops = [
        RouteStopRead(
            order=index,
            place_id=place.id,
            name=place.name,
            estimated_travel_minutes=15 + (index * 5),
        )
        for index, place in enumerate(ordered, start=1)
    ]
    starting_buffer = 10 if payload.start_place else 0
    total = starting_buffer + sum(stop.estimated_travel_minutes for stop in route_stops)
    return RouteOptimizationResponse(
        trip_id=trip_id,
        transport_mode=payload.transport_mode,
        stops=route_stops,
        total_estimated_minutes=total,
    )


@synchronized
def build_replan_from_schedule(
    state: AppState,
    trip_id: str,
    delay_minutes: int,
    current_item_id: str | None,
) -> PlanDraftRead:
    trip = require_trip(state, trip_id)
    current_item = (
        require_schedule_item(state, trip_id, current_item_id)
        if current_item_id is not None
        else None
    )
    schedule = list_schedule(state, trip_id)
    # 지연은 기준 항목이 속한 날짜 안의 문제이므로 다른 날짜의 일정은 밀지 않는다.
    anchor_date = (
        current_item.date
        if current_item is not None
        else next((item.date for item in schedule.items), None)
    )
    shift_suffix = current_item_id is None
    stops_by_date: dict[date, list[PlanStopRead]] = {}
    total_minutes = 0

    for item in schedule.items:
        if item.id == current_item_id:
            shift_suffix = True
        offset = delay_minutes if shift_suffix and item.date == anchor_date else 0
        try:
            shifted_start = shift_datetime(item.date, item.start_time, offset)
            shifted_end = shift_datetime(item.date, item.end_time, offset)
        except OverflowError as exc:
            raise DomainValidationError(REPLAN_RANGE_ERROR) from exc
        if shifted_start.date() < trip.start_date or shifted_end.date() > trip.end_date:
            raise DomainValidationError(REPLAN_RANGE_ERROR)
        if (
            shifted_start.date() != item.date
            or shifted_end.date() != item.date
            or shifted_start.date() != shifted_end.date()
        ):
            raise DomainValidationError(REPLAN_DAY_ERROR)
        stop = PlanStopRead(
            id=state.next_id("stop"),
            place_id=item.place_id,
            name=item.name,
            date=shifted_start.date(),
            start_time=shifted_start.time(),
            end_time=shifted_end.time(),
            notes=item.notes,
            source=item.source,
        )
        stops_by_date.setdefault(stop.date, []).append(stop)
        total_minutes += int((shifted_end - shifted_start).total_seconds() // 60)

    days = [
        PlanDayRead(date=day, stops=stops)
        for day, stops in sorted(stops_by_date.items())
    ]
    plan = PlanDraftRead(
        id=state.next_id("plan"),
        trip_id=trip_id,
        title=f"{trip.title} replanned",
        days=days,
        estimated_total_minutes=total_minutes,
    )
    state.plans[plan.id] = plan
    return plan
