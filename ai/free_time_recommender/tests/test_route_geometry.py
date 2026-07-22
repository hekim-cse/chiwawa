# 경로 geometry 순수 도메인 모델 단위 테스트
from datetime import datetime, timezone
from typing import cast

import pytest

from ai.free_time_recommender.domain.route_geometry import (
    GeoCoordinate,
    RouteGeometryQuery,
    RouteLegGeometry,
    RouteTravelMode,
)


# 유효한 좌표 생성 헬퍼
def coordinate() -> GeoCoordinate:
    return GeoCoordinate(
        latitude=37.5665,
        longitude=126.9780,
    )


# 유효한 경로 geometry 조회 조건 생성 검증
def test_route_geometry_query_accepts_valid_values() -> None:
    departure_at = datetime(
        2026,
        8,
        1,
        10,
        tzinfo=timezone.utc,
    )

    query = RouteGeometryQuery(
        origin=coordinate(),
        destination=GeoCoordinate(37.5700, 126.9900),
        travel_mode=RouteTravelMode.TRANSIT,
        departure_at=departure_at,
    )

    assert query.travel_mode is RouteTravelMode.TRANSIT
    assert query.departure_at == departure_at


# 위도·경도의 경계값 포함 허용 검증
@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (-90.0, -180.0),
        (90.0, 180.0),
        (0.0, 0.0),
    ],
)
def test_coordinate_accepts_boundary_values(
    latitude: float,
    longitude: float,
) -> None:
    result = GeoCoordinate(latitude, longitude)

    assert result.latitude == latitude
    assert result.longitude == longitude


# 좌표의 잘못된 타입·비유한 값·범위 초과 거부 검증
@pytest.mark.parametrize(
    ("field_name", "invalid_value", "exception_type"),
    [
        ("latitude", True, TypeError),
        ("longitude", "126.9", TypeError),
        ("latitude", float("nan"), ValueError),
        ("longitude", float("inf"), ValueError),
        ("latitude", 90.1, ValueError),
        ("longitude", -180.1, ValueError),
    ],
)
def test_coordinate_rejects_invalid_values(
    field_name: str,
    invalid_value: object,
    exception_type: type[Exception],
) -> None:
    values = {
        "latitude": 37.5665,
        "longitude": 126.9780,
    }
    values[field_name] = cast(float, invalid_value)

    with pytest.raises(exception_type):
        GeoCoordinate(**values)


# 대중교통 조회에서 출발시각 누락 거부 검증
def test_transit_query_requires_departure_at() -> None:
    with pytest.raises(
        ValueError,
        match="TRANSIT 경로",
    ):
        RouteGeometryQuery(
            origin=coordinate(),
            destination=coordinate(),
            travel_mode=RouteTravelMode.TRANSIT,
        )


# 출발시각의 timezone-naive 값 거부 검증
def test_query_rejects_timezone_naive_departure_at() -> None:
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        RouteGeometryQuery(
            origin=coordinate(),
            destination=coordinate(),
            travel_mode=RouteTravelMode.WALK,
            departure_at=datetime(2026, 8, 1, 10),
        )


# encoded polyline 빈 값과 잘못된 타입 거부 검증
@pytest.mark.parametrize(
    ("invalid_value", "exception_type"),
    [
        ("", ValueError),
        ("   ", ValueError),
        (1, TypeError),
    ],
)
def test_route_leg_geometry_rejects_invalid_polyline(
    invalid_value: object,
    exception_type: type[Exception],
) -> None:
    with pytest.raises(exception_type):
        RouteLegGeometry(
            encoded_polyline=cast(str, invalid_value),
        )
