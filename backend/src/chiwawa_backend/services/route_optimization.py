# Backend 경로 최적화 요청과 Modal 통합 계약을 변환하는 서비스
from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Protocol

from chiwawa_backend.errors import DomainValidationError, UpstreamServiceError
from chiwawa_backend.schemas.ai_planning import (
    FreeTimeRecommendationsRead,
    RecommendationGroupRead,
    RouteOptionRead,
    TimelineRead,
    TravelMode,
    TripPlanningPOI,
    TripPlanningRequest,
    TripPlanningWithRecommendationsResponse,
)
from chiwawa_backend.schemas.base import PlaceSource, TravelStyle
from chiwawa_backend.schemas.plans import (
    ConfirmedRouteOptimizationRead,
    ConfirmedRouteOptimizationsResponse,
    RouteOptimizationConfirmRequest,
    RouteOptimizationRequest,
    RouteOptimizationResponse,
    RouteStopRead,
)
from chiwawa_backend.schemas.schedule import ScheduleItemCreateRequest, ScheduleResponse
from chiwawa_backend.services.common import require_trip, require_wanted_place
from chiwawa_backend.services.schedule import (
    create_schedule_item,
    ensure_no_schedule_overlap,
    list_schedule,
    validate_schedule_item,
)
from chiwawa_backend.state import synchronized

if TYPE_CHECKING:
    from chiwawa_backend.state import AppState

MISSING_ENDPOINTS_MESSAGE = "출발지와 도착지 정보를 모두 입력해 주세요."
MISSING_WANTED_PLACES_MESSAGE = "최적화할 방문 장소를 한 개 이상 선택해 주세요."
ENDPOINT_ONLY_WANTED_PLACES_MESSAGE = (
    "출발지·도착지와 다른 방문 장소를 한 개 이상 선택해 주세요."
)
MISSING_COORDINATE_MESSAGE = "장소 좌표가 없어 경로를 최적화할 수 없습니다: {name}"
MISSING_PROVIDER_PLACE_ID_MESSAGE = (
    "Google Place ID가 없어 빈 시간 추천을 생성할 수 없습니다: {name}"
)
INVALID_DAY_INDEX_MESSAGE = "선택한 여행 일차가 여행 기간을 벗어났습니다."
UNAVAILABLE_ROUTE_MESSAGE = "요청한 이동수단의 경로를 생성하지 못했습니다."
UNSUPPORTED_MODE_MESSAGE = "지원하지 않는 이동수단입니다. 허용 값: {supported}"
MISSING_ROUTE_LEG_MESSAGE = "경로 최적화 응답에 POI 진입 구간이 없습니다: {place_id}"
EMPTY_CONFIRMATION_MESSAGE = "확정할 방문 장소가 없습니다."
MULTI_DAY_CONFIRMATION_MESSAGE = "확정 일정은 하루 범위를 넘을 수 없습니다."
OUTSIDE_TRIP_CONFIRMATION_MESSAGE = "확정 일정이 여행 기간을 벗어났습니다."
INVALID_CONFIRMATION_TIME_MESSAGE = "확정 일정의 시간 형식이 올바르지 않습니다."
STALE_CONFIRMATION_MESSAGE = "최근 계산한 경로와 다릅니다. 경로를 다시 계산해 주세요."

STAY_MINUTES_BY_PACE = {
    TravelStyle.RELAXED: 120,
    TravelStyle.BALANCED: 90,
    TravelStyle.PACKED: 60,
}
SAME_PLACE_END_ALIAS_PREFIX = "chiwawa:end:"


@synchronized
def confirm_route_optimization(
    state: AppState,
    trip_id: str,
    payload: RouteOptimizationConfirmRequest,
) -> ScheduleResponse:
    """경로 최적화 Timeline의 POI를 해당 일자 스케줄로 확정한다."""
    trip = require_trip(state, trip_id)
    timeline = payload.timeline
    issued_timeline = state.issued_route_timelines.get(
        (trip_id, timeline.day_index),
    )
    if issued_timeline is None or issued_timeline != timeline:
        raise DomainValidationError(STALE_CONFIRMATION_MESSAGE)
    schedule_key = (trip_id, timeline.day_index)
    endpoints = state.issued_route_endpoints.get(schedule_key)
    issued_response = state.issued_route_responses.get(schedule_key)
    issued_route_option = state.issued_route_options.get(schedule_key)
    issued_timezone = state.issued_route_timezones.get(schedule_key)
    if (
        endpoints is None
        or issued_response is None
        or issued_route_option is None
        or issued_timezone is None
    ):
        raise DomainValidationError(STALE_CONFIRMATION_MESSAGE)
    poi_stops = [stop for stop in timeline.timeline_stops if stop.stop_type == "POI"]
    if not poi_stops:
        raise DomainValidationError(EMPTY_CONFIRMATION_MESSAGE)

    replaced_ids = set(state.confirmed_route_items.get(schedule_key, []))
    requests: list[ScheduleItemCreateRequest] = []
    for stop in poi_stops:
        try:
            arrival = dt.datetime.fromisoformat(stop.arrival_at)
            departure = dt.datetime.fromisoformat(stop.departure_at)
        except ValueError as error:
            raise DomainValidationError(INVALID_CONFIRMATION_TIME_MESSAGE) from error
        if arrival.date() != departure.date():
            raise DomainValidationError(MULTI_DAY_CONFIRMATION_MESSAGE)
        if not trip.start_date <= arrival.date() <= trip.end_date:
            raise DomainValidationError(OUTSIDE_TRIP_CONFIRMATION_MESSAGE)
        request = ScheduleItemCreateRequest(
            name=stop.name,
            date=arrival.date(),
            start_time=arrival.time().replace(tzinfo=None),
            end_time=departure.time().replace(tzinfo=None),
            place_id=stop.place_id,
            source=PlaceSource.PLAN,
        )
        validate_schedule_item(state, trip_id, request)
        ensure_no_schedule_overlap(
            state,
            trip_id,
            request,
            excluded_ids=replaced_ids,
        )
        requests.append(request)

    for item_id in replaced_ids:
        existing = state.schedule_items.get(item_id)
        if existing is not None and existing.trip_id == trip_id:
            del state.schedule_items[item_id]
    created = [create_schedule_item(state, trip_id, request) for request in requests]
    state.confirmed_route_items[schedule_key] = [item.id for item in created]
    state.confirmed_routes[schedule_key] = ConfirmedRouteOptimizationRead(
        day_index=timeline.day_index,
        start=endpoints[0],
        end=endpoints[1],
        route=issued_response,
        route_option=issued_route_option,
        timezone=issued_timezone,
    )
    return list_schedule(state, trip_id)


def list_confirmed_route_optimizations(
    state: AppState,
    trip_id: str,
) -> ConfirmedRouteOptimizationsResponse:
    """여행에 확정된 날짜별 경로를 순서대로 반환한다."""
    _ = require_trip(state, trip_id)
    items = [
        route
        for (route_trip_id, _), route in state.confirmed_routes.items()
        if route_trip_id == trip_id
    ]
    items.sort(key=lambda route: route.day_index)
    return ConfirmedRouteOptimizationsResponse(trip_id=trip_id, items=items)


class RoutePlanner(Protocol):
    async def plan_trip(
        self,
        request: TripPlanningRequest,
        *,
        include_recommendations: bool,
    ) -> TripPlanningWithRecommendationsResponse: ...

    async def recommend_free_time(
        self,
        route_option: RouteOptionRead,
        *,
        timezone: str,
    ) -> FreeTimeRecommendationsRead: ...


def build_modal_request(
    state: AppState,
    trip_id: str,
    payload: RouteOptimizationRequest,
    timezone: str,
) -> TripPlanningRequest:
    trip = require_trip(state, trip_id)
    if payload.start is None or payload.end is None:
        raise DomainValidationError(MISSING_ENDPOINTS_MESSAGE)
    if not payload.wanted_place_ids:
        raise DomainValidationError(MISSING_WANTED_PLACES_MESSAGE)
    date = trip.start_date + dt.timedelta(days=payload.day_index - 1)
    if date > trip.end_date:
        raise DomainValidationError(INVALID_DAY_INDEX_MESSAGE)

    pois = _build_modal_pois(state, trip_id, payload)

    end_place = payload.end
    if payload.start.place_id == payload.end.place_id:
        # Solver Matrix는 노드 ID의 고유성을 요구한다. 같은 실제 장소로 돌아오는
        # 왕복 일정은 END 역할에만 내부 별칭을 부여하고 API 응답에서 원래 ID로 복원한다.
        end_place = payload.end.model_copy(
            update={"place_id": _same_place_end_alias(payload)},
        )

    return TripPlanningRequest.model_validate(
        {
            "trip_id": trip_id,
            "timezone": timezone,
            "days": [
                {
                    "day_index": payload.day_index,
                    "date": date,
                    "start_place": payload.start,
                    "start_time": payload.planned_start_time,
                    "end_place": end_place,
                    "end_time": payload.planned_end_time,
                    "max_place_count": payload.max_place_count,
                },
            ],
            "pois": pois,
        },
    )


def _build_modal_pois(
    state: AppState,
    trip_id: str,
    payload: RouteOptimizationRequest,
) -> list[TripPlanningPOI]:
    """출발·도착지와 중복되지 않는 고유 POI 목록을 구성한다."""
    if payload.start is None or payload.end is None:
        raise DomainValidationError(MISSING_ENDPOINTS_MESSAGE)
    stay_minutes = STAY_MINUTES_BY_PACE[payload.pace]
    pois: list[TripPlanningPOI] = []
    endpoint_place_ids = {payload.start.place_id, payload.end.place_id}
    included_provider_place_ids: set[str] = set()
    included_wanted_place_ids: set[str] = set()
    for wanted_place_id in payload.wanted_place_ids:
        if wanted_place_id in included_wanted_place_ids:
            continue
        included_wanted_place_ids.add(wanted_place_id)
        place = require_wanted_place(state, trip_id, wanted_place_id)
        if place.latitude is None or place.longitude is None:
            raise DomainValidationError(
                MISSING_COORDINATE_MESSAGE.format(name=place.name),
            )
        if payload.include_recommendations and place.provider_place_id is None:
            raise DomainValidationError(
                MISSING_PROVIDER_PLACE_ID_MESSAGE.format(name=place.name),
            )
        provider_place_id = place.provider_place_id or place.id
        if provider_place_id in endpoint_place_ids:
            continue
        if provider_place_id in included_provider_place_ids:
            continue
        included_provider_place_ids.add(provider_place_id)
        pois.append(
            TripPlanningPOI(
                poi_id=place.id,
                place_id=provider_place_id,
                name=place.name,
                lat=place.latitude,
                lng=place.longitude,
                category="ETC",
                estimated_stay_minutes=stay_minutes,
                priority=place.priority,
                must_visit=True,
                preferred_day_index=payload.day_index,
            ),
        )

    if not pois:
        raise DomainValidationError(ENDPOINT_ONLY_WANTED_PLACES_MESSAGE)
    return pois


def route_optimization_date(
    state: AppState,
    trip_id: str,
    payload: RouteOptimizationRequest,
) -> dt.date:
    """시간대 조회에 사용할 여행 일자의 유효성을 먼저 검증한다."""
    trip = require_trip(state, trip_id)
    date = trip.start_date + dt.timedelta(days=payload.day_index - 1)
    if date > trip.end_date:
        raise DomainValidationError(INVALID_DAY_INDEX_MESSAGE)
    return date


def to_route_optimization_response(
    planning: TripPlanningWithRecommendationsResponse,
    payload: RouteOptimizationRequest,
) -> RouteOptimizationResponse:
    requested_mode = _travel_mode(payload.transport_mode)
    day_plan = next(
        (day for day in planning.day_plans if day.day_index == payload.day_index),
        None,
    )
    if day_plan is None:
        raise DomainValidationError(UNAVAILABLE_ROUTE_MESSAGE)
    route_option = next(
        (
            option
            for option in day_plan.route_options
            if option.travel_mode is requested_mode
        ),
        None,
    )
    if route_option is None:
        raise DomainValidationError(UNAVAILABLE_ROUTE_MESSAGE)

    travel_by_destination = {
        leg.destination_place_id: leg.travel_minutes for leg in route_option.route_legs
    }
    internal_id_by_provider_id = {
        poi.place_id: poi.poi_id for poi in day_plan.assigned_pois
    }
    internal_id_by_provider_id.update(_endpoint_aliases(payload))
    poi_stops = [stop for stop in route_option.ordered_stops if stop.stop_type == "POI"]
    stops: list[RouteStopRead] = []
    for index, stop in enumerate(poi_stops, start=1):
        travel_minutes = travel_by_destination.get(stop.place_id)
        if travel_minutes is None:
            raise UpstreamServiceError(
                MISSING_ROUTE_LEG_MESSAGE.format(place_id=stop.place_id),
            )
        stops.append(
            RouteStopRead(
                order=index,
                place_id=internal_id_by_provider_id.get(
                    stop.place_id,
                    stop.place_id,
                ),
                name=stop.name,
                estimated_travel_minutes=travel_minutes,
            ),
        )
    groups = _recommendation_groups(
        planning,
        payload.day_index,
        requested_mode,
        internal_id_by_provider_id,
    )
    warnings = list(
        dict.fromkeys([*planning.warnings, *route_option.warnings]),
    )
    return RouteOptimizationResponse(
        trip_id=planning.trip_id,
        transport_mode=requested_mode.value.lower(),
        stops=stops,
        total_estimated_minutes=route_option.total_travel_minutes,
        timeline=_map_timeline_place_ids(
            route_option.timeline,
            internal_id_by_provider_id,
        ),
        missing_segments=route_option.missing_segments,
        warnings=warnings,
        recommendation_groups=groups,
    )


def _travel_mode(value: str) -> TravelMode:
    try:
        return TravelMode(value.strip().upper())
    except ValueError as error:
        supported = ", ".join(mode.value.lower() for mode in TravelMode)
        message = UNSUPPORTED_MODE_MESSAGE.format(supported=supported)
        raise DomainValidationError(message) from error


def _recommendation_groups(
    planning: TripPlanningWithRecommendationsResponse,
    day_index: int,
    travel_mode: TravelMode,
    place_id_aliases: dict[str, str],
) -> list[RecommendationGroupRead]:
    day = next(
        (item for item in planning.day_recommendations if item.day_index == day_index),
        None,
    )
    if day is None:
        return []
    outcome = next(
        (
            item
            for item in day.route_options
            if item.route_option.travel_mode is travel_mode
        ),
        None,
    )
    if outcome is None or outcome.recommendation is None:
        return []
    return [
        group.model_copy(
            update={
                "recommendations": [
                    recommendation.model_copy(
                        update={
                            "window": recommendation.window.model_copy(
                                update={
                                    "previous_place_id": place_id_aliases.get(
                                        recommendation.window.previous_place_id,
                                        recommendation.window.previous_place_id,
                                    ),
                                    "next_place_id": place_id_aliases.get(
                                        recommendation.window.next_place_id,
                                        recommendation.window.next_place_id,
                                    ),
                                },
                            ),
                        },
                    )
                    for recommendation in group.recommendations
                ],
            },
        )
        for group in outcome.recommendation.recommendation_groups
    ]


def _same_place_end_alias(payload: RouteOptimizationRequest) -> str:
    if payload.end is None:
        raise DomainValidationError(MISSING_ENDPOINTS_MESSAGE)
    return f"{SAME_PLACE_END_ALIAS_PREFIX}{payload.day_index}:{payload.end.place_id}"


def _endpoint_aliases(payload: RouteOptimizationRequest) -> dict[str, str]:
    if payload.start is None or payload.end is None:
        return {}
    if payload.start.place_id != payload.end.place_id:
        return {}
    return {_same_place_end_alias(payload): payload.end.place_id}


def _map_timeline_place_ids(
    timeline: TimelineRead | None,
    internal_id_by_provider_id: dict[str, str],
) -> TimelineRead | None:
    """외부 Provider ID를 기존 Backend 장소 ID 계약으로 복원한다."""
    if timeline is None:
        return None
    return timeline.model_copy(
        update={
            "timeline_stops": [
                stop.model_copy(
                    update={
                        "place_id": internal_id_by_provider_id.get(
                            stop.place_id,
                            stop.place_id,
                        ),
                    },
                )
                for stop in timeline.timeline_stops
            ],
        },
    )
