from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from chiwawa_backend.schemas.ai_planning import TripPlanningRequest

if TYPE_CHECKING:
    from collections.abc import Sequence

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


def _place(place_id: str) -> JsonObject:
    return {
        "place_id": place_id,
        "name": place_id,
        "lat": 35.0,
        "lng": 139.0,
    }


def _day(
    day_index: int,
    date: str,
    *,
    start_time: str = "09:00",
    end_time: str = "18:00",
) -> JsonObject:
    return {
        "day_index": day_index,
        "date": date,
        "start_place": _place(f"start-{day_index}"),
        "start_time": start_time,
        "end_place": _place(f"end-{day_index}"),
        "end_time": end_time,
    }


def _poi(
    *,
    category: str = "CAFE",
    preferred_day_index: int | None = None,
) -> JsonObject:
    return {
        "poi_id": "poi-1",
        "place_id": "place-1",
        "name": "Cafe",
        "lat": 35.0,
        "lng": 139.0,
        "category": category,
        "estimated_stay_minutes": 60,
        "priority": 3,
        "must_visit": True,
        "preferred_day_index": preferred_day_index,
    }


def _request(
    days: Sequence[JsonValue],
    pois: Sequence[JsonValue],
) -> JsonObject:
    return {
        "trip_id": "trip-1",
        "timezone": "Asia/Tokyo",
        "days": list(days),
        "pois": list(pois),
    }


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [
        ("18:00", "09:00"),
        ("09:00:00", "18:00:00"),
        ("09:00+09:00", "18:00"),
        ("09:00", "18:00+09:00"),
    ],
)
def test_day_rejects_reversed_or_offset_times(
    start_time: str,
    end_time: str,
) -> None:
    payload = _request(
        [_day(1, "2026-08-01", start_time=start_time, end_time=end_time)],
        [_poi()],
    )

    with pytest.raises(ValidationError):
        _ = TripPlanningRequest.model_validate(payload)


@pytest.mark.parametrize(
    "days",
    [
        [_day(1, "2026-08-01"), _day(1, "2026-08-02")],
        [_day(1, "2026-08-01"), _day(2, "2026-08-01")],
        [_day(1, "2026-08-01"), _day(3, "2026-08-02")],
        [_day(1, "2026-08-02"), _day(2, "2026-08-01")],
    ],
)
def test_request_rejects_inconsistent_day_sequence(
    days: list[JsonObject],
) -> None:
    with pytest.raises(ValidationError):
        _ = TripPlanningRequest.model_validate(_request(days, [_poi()]))


def test_request_rejects_empty_pois() -> None:
    with pytest.raises(ValidationError):
        _ = TripPlanningRequest.model_validate(
            _request([_day(1, "2026-08-01")], []),
        )


def test_request_rejects_unknown_poi_category() -> None:
    with pytest.raises(ValidationError):
        _ = TripPlanningRequest.model_validate(
            _request([_day(1, "2026-08-01")], [_poi(category="UNKNOWN")]),
        )


def test_request_rejects_missing_preferred_day() -> None:
    with pytest.raises(ValidationError):
        _ = TripPlanningRequest.model_validate(
            _request(
                [_day(1, "2026-08-01")],
                [_poi(preferred_day_index=2)],
            ),
        )
