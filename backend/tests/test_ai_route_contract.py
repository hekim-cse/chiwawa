from __future__ import annotations

import pytest
from pydantic import ValidationError

from chiwawa_backend.schemas.ai_planning import (
    TripPlanningResponse,
    TripPlanningStatus,
    TripPlanningTravelMode,
)


def test_response_parses_partial_success_route_timeline_contract() -> None:
    response = TripPlanningResponse.model_validate(
        {
            "trip_id": "trip-1",
            "status": "PARTIAL_SUCCESS",
            "day_plans": [
                {
                    "day_index": 1,
                    "date": "2026-08-01",
                    "start_place": {
                        "place_id": "start",
                        "name": "Start",
                        "lat": 35.0,
                        "lng": 139.0,
                    },
                    "end_place": {
                        "place_id": "end",
                        "name": "End",
                        "lat": 35.1,
                        "lng": 139.1,
                    },
                    "assigned_pois": [],
                    "estimated_total_stay_minutes": 0,
                    "assignment_reason": "No assignable POI.",
                    "route_options": [
                        {
                            "day_index": 1,
                            "travel_mode": "TRANSIT",
                            "total_travel_minutes": 20,
                            "ordered_stops": [
                                {
                                    "stop_type": "START",
                                    "place_id": "start",
                                    "name": "Start",
                                    "lat": 35.0,
                                    "lng": 139.0,
                                },
                                {
                                    "stop_type": "END",
                                    "place_id": "end",
                                    "name": "End",
                                    "lat": 35.1,
                                    "lng": 139.1,
                                },
                            ],
                            "route_legs": [
                                {
                                    "origin_place_id": "start",
                                    "destination_place_id": "end",
                                    "travel_minutes": 20,
                                }
                            ],
                            "missing_segments": [],
                            "warnings": [],
                            "timeline": {
                                "day_index": 1,
                                "travel_mode": "TRANSIT",
                                "planned_start_at": "2026-08-01T09:00",
                                "planned_end_at": "2026-08-01T18:00",
                                "actual_end_at": "2026-08-01T09:20",
                                "total_travel_minutes": 20,
                                "total_stay_minutes": 0,
                                "timeline_stops": [
                                    {
                                        "stop_type": "START",
                                        "place_id": "start",
                                        "name": "Start",
                                        "arrival_at": "2026-08-01T09:00",
                                        "departure_at": "2026-08-01T09:00",
                                        "stay_minutes": 0,
                                    }
                                ],
                                "exceeds_planned_end": False,
                                "warnings": [],
                            },
                        }
                    ],
                }
            ],
            "unassigned_pois": [],
            "warnings": ["One POI was not assigned."],
        }
    )

    route = response.day_plans[0].route_options[0]
    assert response.status is TripPlanningStatus.PARTIAL_SUCCESS
    assert route.travel_mode is TripPlanningTravelMode.TRANSIT
    assert route.timeline is not None
    assert route.timeline.actual_end_at == "2026-08-01T09:20"


def test_response_requires_day_plans_field() -> None:
    with pytest.raises(ValidationError):
        _ = TripPlanningResponse.model_validate(
            {"trip_id": "trip-1", "status": "FAILED"}
        )
