# 추천 후보 경유 이동 지표 도메인 모델 테스트
from datetime import datetime, timezone

import pytest

from ai.free_time_recommender.domain.candidate_route_metrics import (
    CandidateRouteMetricsQuery,
    RouteLegMetrics,
)
from ai.free_time_recommender.domain.route_geometry import RouteTravelMode


def make_query(**updates: object) -> CandidateRouteMetricsQuery:
    values: dict[str, object] = {
        "previous_place_id": "도쿄역-place-id",
        "candidate_place_id": "도쿄타워-place-id",
        "next_place_id": "시부야역-place-id",
        "previous_departure_at": datetime(
            2026, 8, 1, 10, tzinfo=timezone.utc
        ),
        "stay_minutes": 60,
        "travel_mode": RouteTravelMode.TRANSIT,
    }
    values.update(updates)
    return CandidateRouteMetricsQuery(**values)


@pytest.mark.parametrize(
    "updates",
    [
        {"previous_place_id": ""},
        {"candidate_place_id": "도쿄역-place-id"},
        {"previous_departure_at": datetime(2026, 8, 1, 10)},
        {"stay_minutes": 0},
        {"stay_minutes": True},
        {"travel_mode": "TRANSIT"},
    ],
)
def test_query_rejects_invalid_values(updates: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        make_query(**updates)


@pytest.mark.parametrize(
    ("travel_minutes", "distance_meters", "expected"),
    [(-1, 0, ValueError), (0, -1, ValueError), (True, 0, TypeError)],
)
def test_leg_metrics_rejects_invalid_values(
    travel_minutes: object,
    distance_meters: object,
    expected: type[Exception],
) -> None:
    with pytest.raises(expected):
        RouteLegMetrics(
            travel_minutes=travel_minutes,
            distance_meters=distance_meters,
        )
