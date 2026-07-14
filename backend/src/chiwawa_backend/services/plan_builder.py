from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

from chiwawa_backend.errors import DomainValidationError
from chiwawa_backend.schemas.base import PlaceSource, TravelStyle
from chiwawa_backend.schemas.plans import PlanDayRead, PlanDraftRead, PlanStopRead
from chiwawa_backend.services.common import require_trip

if TYPE_CHECKING:
    from chiwawa_backend.state import AppState

TRAVEL_BUFFER_MINUTES = 30
PLAN_WINDOW_ERROR = "preferred time window is too short for the selected pace"


@dataclass(frozen=True, slots=True)
class PlanBuildOptions:
    title: str
    start_time: time
    end_time: time
    pace: TravelStyle


def build_plan(
    state: AppState,
    trip_id: str,
    options: PlanBuildOptions,
) -> PlanDraftRead:
    trip = require_trip(state, trip_id)
    places = [
        place for place in state.wanted_places.values() if place.trip_id == trip_id
    ]
    candidates = sorted(places, key=lambda place: (-place.priority, place.name))
    if not candidates:
        return _empty_city_plan(state, trip_id, trip.start_date, trip.city, options)

    stop_minutes = _stop_minutes(options.pace)
    available_minutes = int(
        (
            datetime.combine(trip.start_date, options.end_time)
            - datetime.combine(trip.start_date, options.start_time)
        ).total_seconds()
        // 60,
    )
    if available_minutes < stop_minutes:
        raise DomainValidationError(PLAN_WINDOW_ERROR)

    days: list[PlanDayRead] = []
    candidate_index = 0
    day_count = (trip.end_date - trip.start_date).days + 1
    for day_offset in range(day_count):
        day = trip.start_date + timedelta(days=day_offset)
        cursor = datetime.combine(day, options.start_time)
        window_end = datetime.combine(day, options.end_time)
        stops: list[PlanStopRead] = []
        stop_duration = timedelta(minutes=stop_minutes)
        travel_buffer = timedelta(minutes=TRAVEL_BUFFER_MINUTES)
        while candidate_index < len(candidates):
            if window_end - cursor < stop_duration:
                break
            stop_end = cursor + stop_duration
            place = candidates[candidate_index]
            stops.append(
                PlanStopRead(
                    id=state.next_id("stop"),
                    place_id=place.id,
                    name=place.name,
                    date=day,
                    start_time=cursor.time(),
                    end_time=stop_end.time(),
                    notes=place.notes,
                    source=place.source,
                ),
            )
            candidate_index += 1
            if (
                candidate_index == len(candidates)
                or window_end - stop_end < travel_buffer
            ):
                break
            cursor = stop_end + travel_buffer
        if stops:
            days.append(PlanDayRead(date=day, stops=stops))
        if candidate_index == len(candidates):
            break

    return PlanDraftRead(
        id=state.next_id("plan"),
        trip_id=trip_id,
        title=options.title,
        days=days,
        estimated_total_minutes=candidate_index * stop_minutes,
    )


def shift_datetime(day: date, value: time, minutes: int) -> datetime:
    return datetime.combine(day, value) + timedelta(minutes=minutes)


def _empty_city_plan(
    state: AppState,
    trip_id: str,
    start_date: date,
    city: str,
    options: PlanBuildOptions,
) -> PlanDraftRead:
    start = datetime.combine(start_date, options.start_time)
    window_end = datetime.combine(start_date, options.end_time)
    duration = min(90, int((window_end - start).total_seconds() // 60))
    stop_end = start + timedelta(minutes=duration)
    stop = PlanStopRead(
        id=state.next_id("stop"),
        place_id=None,
        name=f"{city} orientation walk",
        date=start_date,
        start_time=start.time(),
        end_time=stop_end.time(),
        notes="Add wanted places to get a more specific route.",
        source=PlaceSource.PLAN,
    )
    return PlanDraftRead(
        id=state.next_id("plan"),
        trip_id=trip_id,
        title=options.title,
        days=[PlanDayRead(date=start_date, stops=[stop])],
        estimated_total_minutes=duration,
    )


def _stop_minutes(pace: TravelStyle) -> int:
    match pace:
        case TravelStyle.RELAXED:
            return 120
        case TravelStyle.BALANCED:
            return 90
        case TravelStyle.PACKED:
            return 60
