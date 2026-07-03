from datetime import date, datetime, time, timedelta

from chiwawa_backend.schemas.base import PlaceSource, PlanJobStatus, TravelStyle
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
    require_trip,
)
from chiwawa_backend.services.schedule import create_schedule_item, list_schedule
from chiwawa_backend.state import AppState


def create_plan_job(
    state: AppState,
    trip_id: str,
    payload: AIPlanCreateRequest,
) -> PlanJobRead:
    trip = require_trip(state, trip_id)
    pace = payload.pace or trip.travel_style
    plan = _build_plan(
        state=state,
        trip_id=trip_id,
        title=f"{trip.title} AI draft",
        start_time=payload.preferred_start_time,
        pace=pace,
    )
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


def get_plan_job(state: AppState, trip_id: str, job_id: str) -> PlanJobRead:
    return require_plan_job(state, trip_id, job_id)


def get_plan(state: AppState, trip_id: str, plan_id: str) -> PlanDraftRead:
    return require_plan(state, trip_id, plan_id)


def confirm_plan(state: AppState, trip_id: str, plan_id: str) -> PlanConfirmResponse:
    plan = require_plan(state, trip_id, plan_id)
    for day in plan.days:
        for stop in day.stops:
            _ = create_schedule_item(
                state=state,
                trip_id=trip_id,
                payload=ScheduleItemCreateRequest(
                    name=stop.name,
                    date=stop.date,
                    start_time=stop.start_time,
                    end_time=stop.end_time,
                    place_id=stop.place_id,
                    notes=stop.notes,
                    source=PlaceSource.PLAN,
                ),
            )
    return PlanConfirmResponse(plan=plan, schedule=list_schedule(state, trip_id))


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


def build_replan_from_schedule(
    state: AppState,
    trip_id: str,
    delay_minutes: int,
) -> PlanDraftRead:
    trip = require_trip(state, trip_id)
    schedule = list_schedule(state, trip_id)
    stops = [
        PlanStopRead(
            id=state.next_id("stop"),
            place_id=item.place_id,
            name=item.name,
            date=item.date,
            start_time=_shift_time(item.date, item.start_time, delay_minutes),
            end_time=_shift_time(item.date, item.end_time, delay_minutes),
            notes=item.notes,
            source=item.source,
        )
        for item in schedule.items
    ]
    day = PlanDayRead(date=trip.start_date, stops=stops)
    plan = PlanDraftRead(
        id=state.next_id("plan"),
        trip_id=trip_id,
        title=f"{trip.title} replanned",
        days=[day],
        estimated_total_minutes=len(stops) * 90,
    )
    state.plans[plan.id] = plan
    return plan


def _build_plan(
    state: AppState,
    trip_id: str,
    title: str,
    start_time: time,
    pace: TravelStyle,
) -> PlanDraftRead:
    trip = require_trip(state, trip_id)
    places = [
        place for place in state.wanted_places.values() if place.trip_id == trip_id
    ]
    candidates = sorted(places, key=lambda place: (-place.priority, place.name))
    if not candidates:
        return _empty_city_plan(state, trip_id, title, trip.start_date, trip.city)
    stop_minutes = _stop_minutes(pace)
    stops_by_date: dict[date, list[PlanStopRead]] = {}
    for index, place in enumerate(candidates):
        offset = index % ((trip.end_date - trip.start_date).days + 1)
        day = trip.start_date + timedelta(days=offset)
        start = _shift_time(day, start_time, (index // 2) * (stop_minutes + 30))
        stop = PlanStopRead(
            id=state.next_id("stop"),
            place_id=place.id,
            name=place.name,
            date=day,
            start_time=start,
            end_time=_shift_time(day, start, stop_minutes),
            notes=place.notes,
            source=place.source,
        )
        stops_by_date.setdefault(day, []).append(stop)
    days = [
        PlanDayRead(date=day, stops=sorted(stops, key=lambda stop: stop.start_time))
        for day, stops in sorted(stops_by_date.items())
    ]
    total_minutes = len(candidates) * stop_minutes
    return PlanDraftRead(
        id=state.next_id("plan"),
        trip_id=trip_id,
        title=title,
        days=days,
        estimated_total_minutes=total_minutes,
    )


def _empty_city_plan(
    state: AppState,
    trip_id: str,
    title: str,
    start_date: date,
    city: str,
) -> PlanDraftRead:
    stop = PlanStopRead(
        id=state.next_id("stop"),
        place_id=None,
        name=f"{city} orientation walk",
        date=start_date,
        start_time=time(hour=10),
        end_time=time(hour=11, minute=30),
        notes="Add wanted places to get a more specific route.",
        source=PlaceSource.PLAN,
    )
    day = PlanDayRead(date=start_date, stops=[stop])
    return PlanDraftRead(
        id=state.next_id("plan"),
        trip_id=trip_id,
        title=title,
        days=[day],
        estimated_total_minutes=90,
    )


def _stop_minutes(pace: TravelStyle) -> int:
    match pace:
        case TravelStyle.RELAXED:
            return 120
        case TravelStyle.BALANCED:
            return 90
        case TravelStyle.PACKED:
            return 60


def _shift_time(day: date, value: time, minutes: int) -> time:
    shifted = datetime.combine(day, value) + timedelta(minutes=minutes)
    return shifted.time()
