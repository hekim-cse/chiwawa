from __future__ import annotations

import datetime as dt

import pytest
from pydantic import ValidationError

from chiwawa_backend.schemas.ai_planning import (
    TripPlanningRequest,
    TripPlanningResponse,
    TripPlanningStatus,
)


def test_trip_planning_request_parses_pdf_contract() -> None:
    # Given: the backend-to-AI request shape from the DTO design.
    payload = {
        "trip_id": "trip_001",
        "timezone": "Asia/Tokyo",
        "days": [
            {
                "day_index": 1,
                "date": "2026-08-01",
                "start_place": {
                    "place_id": "place_start_1",
                    "name": "Osaka Namba Station",
                    "lat": 34.6657531,
                    "lng": 135.5010362,
                },
                "start_time": "10:00",
                "end_place": {
                    "place_id": "place_end_1",
                    "name": "Umeda Sky Building",
                    "lat": 34.7052872,
                    "lng": 135.4896527,
                },
                "end_time": "20:00",
                "max_place_count": 5,
            },
        ],
        "pois": [
            {
                "poi_id": "poi_001",
                "place_id": "google_place_001",
                "name": "Dotonbori",
                "lat": 34.6686471,
                "lng": 135.5030983,
                "category": "TOURIST_ATTRACTION",
                "estimated_stay_minutes": 60,
                "priority": 1,
                "must_visit": True,
                "preferred_day_index": None,
            },
        ],
    }

    # When: the boundary model parses the JSON-compatible payload.
    request = TripPlanningRequest.model_validate(payload)

    # Then: date and time strings become typed values while JSON field names remain.
    assert request.trip_id == "trip_001"
    assert request.timezone == "Asia/Tokyo"
    assert request.days[0].date == dt.date(2026, 8, 1)
    assert request.days[0].start_time == dt.time(10)
    assert request.model_dump(mode="json")["days"][0]["start_time"] == "10:00"
    assert request.pois[0].must_visit is True


def test_trip_planning_response_serializes_ai_assignment_contract() -> None:
    # Given: an AI-to-backend day assignment response.
    response = TripPlanningResponse.model_validate(
        {
            "trip_id": "trip_001",
            "status": "SUCCESS",
            "day_plans": [
                {
                    "day_index": 1,
                    "date": "2026-08-01",
                    "start_place": {
                        "place_id": "place_start_1",
                        "name": "Osaka Namba Station",
                        "lat": 34.6657531,
                        "lng": 135.5010362,
                    },
                    "end_place": {
                        "place_id": "place_end_1",
                        "name": "Umeda Sky Building",
                        "lat": 34.7052872,
                        "lng": 135.4896527,
                    },
                    "assigned_pois": [
                        {
                            "poi_id": "poi_001",
                            "place_id": "google_place_001",
                            "name": "Dotonbori",
                            "lat": 34.6686471,
                            "lng": 135.5030983,
                            "category": "TOURIST_ATTRACTION",
                            "estimated_stay_minutes": 60,
                            "priority": 1,
                            "must_visit": True,
                            "preferred_day_index": None,
                        },
                    ],
                    "estimated_total_stay_minutes": 60,
                    "assignment_reason": "Close to the start area.",
                },
            ],
            "unassigned_pois": [],
            "warnings": [],
        },
    )

    # When: the backend serializes the parsed AI result.
    data = response.model_dump(mode="json")

    # Then: the wire contract stays compatible with the PDF examples.
    assert data["trip_id"] == "trip_001"
    assert data["status"] == TripPlanningStatus.SUCCESS
    assert data["day_plans"][0]["date"] == "2026-08-01"
    assert data["day_plans"][0]["assigned_pois"][0]["poi_id"] == "poi_001"


def test_trip_planning_request_rejects_invalid_boundary_values() -> None:
    # Given: malformed AI-boundary input with an invalid timezone and latitude.
    payload = {
        "trip_id": "trip_001",
        "timezone": "Tokyo",
        "days": [
            {
                "day_index": 1,
                "date": "2026-08-01",
                "start_place": {
                    "place_id": "place_start_1",
                    "name": "Osaka Namba Station",
                    "lat": 91,
                    "lng": 135.5010362,
                },
                "start_time": "10:00",
                "end_place": {
                    "place_id": "place_end_1",
                    "name": "Umeda Sky Building",
                    "lat": 34.7052872,
                    "lng": 135.4896527,
                },
                "end_time": "20:00",
                "unknown": "extra",
            },
        ],
        "pois": [],
    }

    # When / Then: the boundary rejects invalid data before it reaches AI.
    with pytest.raises(ValidationError):
        _ = TripPlanningRequest.model_validate(payload)


def test_trip_planning_request_rejects_second_precision_time() -> None:
    # Given: AI-boundary input with seconds in a day boundary time.
    payload = {
        "trip_id": "trip_001",
        "timezone": "Asia/Tokyo",
        "days": [
            {
                "day_index": 1,
                "date": "2026-08-01",
                "start_place": {
                    "place_id": "place_start_1",
                    "name": "Osaka Namba Station",
                    "lat": 34.6657531,
                    "lng": 135.5010362,
                },
                "start_time": "10:00:30",
                "end_place": {
                    "place_id": "place_end_1",
                    "name": "Umeda Sky Building",
                    "lat": 34.7052872,
                    "lng": 135.4896527,
                },
                "end_time": "20:00",
            },
        ],
        "pois": [],
    }

    # When / Then: the boundary keeps the PDF contract at HH:MM precision.
    with pytest.raises(ValidationError):
        _ = TripPlanningRequest.model_validate(payload)
