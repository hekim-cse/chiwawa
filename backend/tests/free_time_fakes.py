# 실제 경로 최적화 응답 구조로 빈 시간 추천 API를 검증하기 위한 fixture
import datetime as dt

from chiwawa_backend.schemas.ai_planning import (
    FreeTimeRecommendationsRead,
    RecommendationGroupRead,
    RouteOptionRead,
    TimelineRead,
)
from chiwawa_backend.schemas.plans import ConfirmedRouteOptimizationRead
from chiwawa_backend.state import AppState


def seed_free_time_recommendation_context(
    state: AppState,
    trip_id: str,
    *,
    day_index: int = 1,
    candidate_arrival_at: dt.datetime | None = None,
) -> None:
    """Google Provider 검증을 마친 Modal 응답과 같은 형태를 저장한다."""
    arrival = candidate_arrival_at or dt.datetime(
        2026,
        7,
        10,
        15,
        tzinfo=dt.UTC,
    )
    departure = arrival + dt.timedelta(minutes=60)
    route_key = (trip_id, day_index)
    state.issued_route_timelines[route_key] = TimelineRead.model_validate(
        {
            "day_index": day_index,
            "travel_mode": "WALK",
            "planned_start_at": arrival.replace(hour=9).isoformat(),
            "planned_end_at": arrival.replace(hour=20).isoformat(),
            "actual_end_at": departure.isoformat(),
            "total_travel_minutes": 20,
            "total_stay_minutes": 60,
            "timeline_stops": [],
        },
    )
    state.issued_route_recommendations[route_key] = [
        RecommendationGroupRead.model_validate(
            {
                "category": "LANDMARK",
                "display_name": "랜드마크·관광명소",
                "recommendations": [
                    {
                        "candidate": {
                            "place_id": "google-test-landmark",
                            "name": "추천 전망대",
                            "coordinate": {
                                "latitude": 35.658,
                                "longitude": 139.702,
                            },
                            "category": "LANDMARK",
                        },
                        "window": {
                            "day_index": day_index,
                            "leg_index": 0,
                            "previous_place_id": "start",
                            "next_place_id": "end",
                            "previous_departure_at": arrival - dt.timedelta(minutes=10),
                            "next_arrival_at": departure + dt.timedelta(minutes=10),
                            "original_travel_minutes": 10,
                            "original_timeline_end_at": departure,
                            "planned_end_at": arrival.replace(hour=20),
                        },
                        "route_metrics": {
                            "previous_to_candidate": {
                                "travel_minutes": 5,
                                "distance_meters": 400,
                            },
                            "candidate_to_next": {
                                "travel_minutes": 5,
                                "distance_meters": 400,
                            },
                            "candidate_arrival_at": arrival,
                            "candidate_departure_at": departure,
                            "next_arrival_at": departure + dt.timedelta(minutes=5),
                        },
                        "insertion_impact": {
                            "replacement_travel_minutes": 10,
                            "replacement_total_minutes": 70,
                            "additional_minutes": 60,
                            "updated_next_arrival_at": departure
                            + dt.timedelta(minutes=5),
                            "updated_timeline_end_at": departure,
                            "remaining_minutes": 120,
                            "rejection_reasons": [],
                        },
                    },
                ],
            },
        ),
    ]
    route_option = RouteOptionRead.model_validate(
        {
            "day_index": day_index,
            "travel_mode": "WALK",
            "total_travel_minutes": 20,
            "ordered_stops": [
                {
                    "stop_type": "START",
                    "place_id": "start",
                    "name": "출발지",
                    "lat": 35.65,
                    "lng": 139.70,
                },
                {
                    "stop_type": "END",
                    "place_id": "end",
                    "name": "도착지",
                    "lat": 35.66,
                    "lng": 139.71,
                },
            ],
            "route_legs": [
                {
                    "origin_place_id": "start",
                    "destination_place_id": "end",
                    "travel_minutes": 20,
                }
            ],
            "timeline": state.issued_route_timelines[route_key],
        }
    )
    state.issued_route_options[route_key] = route_option
    state.issued_route_timezones[route_key] = "Europe/Paris"
    state.confirmed_routes[route_key] = ConfirmedRouteOptimizationRead.model_validate(
        {
            "day_index": day_index,
            "start": {
                "place_id": "start",
                "name": "출발지",
                "lat": 35.65,
                "lng": 139.70,
            },
            "end": {
                "place_id": "end",
                "name": "도착지",
                "lat": 35.66,
                "lng": 139.71,
            },
            "route": {
                "trip_id": trip_id,
                "transport_mode": "walk",
                "stops": [],
                "total_estimated_minutes": 20,
                "timeline": state.issued_route_timelines[route_key],
            },
            "route_option": route_option,
            "timezone": "Europe/Paris",
        }
    )


class FakeFreeTimeRoutePlanner:
    def __init__(self, state: AppState, trip_id: str, day_index: int = 1) -> None:
        self._state = state
        self._route_key = (trip_id, day_index)
        self.calls = 0

    async def recommend_free_time(
        self,
        route_option: RouteOptionRead,
        *,
        timezone: str,
    ) -> FreeTimeRecommendationsRead:
        self.calls += 1
        assert timezone == "Europe/Paris"
        return FreeTimeRecommendationsRead.model_validate(
            {
                "route_options": [
                    {
                        "route_option": route_option,
                        "status": "SUCCESS",
                        "recommendation": {
                            "route_option": route_option,
                            "route_leg_geometries": [],
                            "recommendation_groups": (
                                self._state.issued_route_recommendations[
                                    self._route_key
                                ]
                            ),
                        },
                    }
                ]
            }
        )
