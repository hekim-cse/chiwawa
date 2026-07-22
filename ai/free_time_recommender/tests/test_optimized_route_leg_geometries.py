# 최적화 Route Option의 구간별 geometry 변환 및 생성 테스트
from zoneinfo import ZoneInfo

import pytest

from ai.free_time_recommender.adapters.errors import (
    RoutePlannerRouteOptionAdapterError,
)
from ai.free_time_recommender.adapters.route_planner_route_option_adapter import (
    RoutePlannerRouteOptionAdapter,
)
from ai.free_time_recommender.application.build_optimized_route_leg_geometries import (
    BuildOptimizedRouteLegGeometries,
)
from ai.free_time_recommender.domain.route_geometry import (
    RouteGeometryQuery,
    RouteLegGeometry,
    RouteTravelMode,
)
from ai.route_planner.domain.schemas import TravelMode
from ai.route_planner.domain.trip_schemas import (
    RouteLegDTO,
    RouteOptionDTO,
    RouteStopDTO,
    RouteStopType,
    TimelineDTO,
    TimelineStopDTO,
)


class StubRouteGeometryProvider:
    """호출 순서에 대응하는 polyline을 반환하는 테스트 Provider."""

    def __init__(self) -> None:
        self.queries: list[RouteGeometryQuery] = []

    def get_route_geometry(
        self,
        query: RouteGeometryQuery,
    ) -> RouteLegGeometry:
        self.queries.append(query)
        return RouteLegGeometry(f"encoded-leg-{len(self.queries) - 1}")


class FailingRouteGeometryProvider:
    """외부 경로 조회 실패가 숨겨지지 않는지 확인하는 테스트 Provider."""

    def get_route_geometry(
        self,
        query: RouteGeometryQuery,
    ) -> RouteLegGeometry:
        raise RuntimeError("Google Routes 호출 실패")


# 도쿄역 → 도쿄타워 → 시부야역 최적화 Route Option 생성 헬퍼
def make_route_option() -> RouteOptionDTO:
    stops = [
        RouteStopDTO(
            stop_type=RouteStopType.START,
            place_id="tokyo-station",
            name="도쿄역",
            lat=35.6812,
            lng=139.7671,
        ),
        RouteStopDTO(
            stop_type=RouteStopType.POI,
            place_id="tokyo-tower",
            name="도쿄 타워",
            lat=35.6586,
            lng=139.7454,
        ),
        RouteStopDTO(
            stop_type=RouteStopType.END,
            place_id="shibuya-station",
            name="시부야역",
            lat=35.6580,
            lng=139.7016,
        ),
    ]
    timeline_stops = [
        TimelineStopDTO(
            stop_type=stop.stop_type,
            place_id=stop.place_id,
            name=stop.name,
            arrival_at=time,
            departure_at=time,
            stay_minutes=0,
        )
        for stop, time in zip(
            stops,
            (
                "2026-08-01T10:00",
                "2026-08-01T11:00",
                "2026-08-01T12:00",
            ),
        )
    ]
    return RouteOptionDTO(
        day_index=1,
        travel_mode=TravelMode.TRANSIT,
        total_travel_minutes=60,
        ordered_stops=stops,
        route_legs=[
            RouteLegDTO(
                origin_place_id="tokyo-station",
                destination_place_id="tokyo-tower",
                travel_minutes=30,
            ),
            RouteLegDTO(
                origin_place_id="tokyo-tower",
                destination_place_id="shibuya-station",
                travel_minutes=30,
            ),
        ],
        timeline=TimelineDTO(
            day_index=1,
            travel_mode=TravelMode.TRANSIT,
            planned_start_at="2026-08-01T10:00",
            planned_end_at="2026-08-01T18:00",
            actual_end_at="2026-08-01T12:00",
            total_travel_minutes=60,
            total_stay_minutes=0,
            timeline_stops=timeline_stops,
        ),
    )


# 최적화 방문 순서, 좌표, 출발시각을 구간별 내부 요청으로 변환
def test_adapter_builds_queries_for_each_optimized_leg() -> None:
    result = RoutePlannerRouteOptionAdapter().to_geometry_queries(
        make_route_option(),
        ZoneInfo("Asia/Tokyo"),
    )

    assert tuple(item.leg_index for item in result) == (0, 1)
    assert result[0].origin_place_id == "tokyo-station"
    assert result[0].destination_place_id == "tokyo-tower"
    assert result[0].geometry_query.travel_mode is RouteTravelMode.TRANSIT
    assert result[0].geometry_query.departure_at.isoformat() == (
        "2026-08-01T10:00:00+09:00"
    )


# Provider 결과를 원래 구간 순서와 식별 정보에 맞춰 결합하는지 검증
def test_use_case_preserves_leg_order_and_geometry() -> None:
    queries = RoutePlannerRouteOptionAdapter().to_geometry_queries(
        make_route_option(),
        ZoneInfo("Asia/Tokyo"),
    )
    provider = StubRouteGeometryProvider()

    result = BuildOptimizedRouteLegGeometries(
        provider=provider
    ).execute(queries)

    assert tuple(item.leg_index for item in result) == (0, 1)
    assert tuple(item.geometry.encoded_polyline for item in result) == (
        "encoded-leg-0",
        "encoded-leg-1",
    )
    assert len(provider.queries) == 2


# Timeline이 없으면 출발시각을 추측하지 않고 명시적으로 변환을 거부
def test_adapter_rejects_route_option_without_timeline() -> None:
    route_option = make_route_option().model_copy(update={"timeline": None})

    with pytest.raises(
        RoutePlannerRouteOptionAdapterError,
        match="Timeline이 필요합니다",
    ):
        RoutePlannerRouteOptionAdapter().to_geometry_queries(
            route_option,
            ZoneInfo("Asia/Tokyo"),
        )


# 이동시간 누락 구간이 있으면 불완전한 최적화 결과를 후속 API에 전달하지 않음
def test_adapter_rejects_route_option_with_missing_segments() -> None:
    route_option = make_route_option().model_copy(
        update={"missing_segments": ["tokyo-station->tokyo-tower"]}
    )

    with pytest.raises(
        RoutePlannerRouteOptionAdapterError,
        match="이동시간이 누락된",
    ):
        RoutePlannerRouteOptionAdapter().to_geometry_queries(
            route_option,
            ZoneInfo("Asia/Tokyo"),
        )


# Timeline의 전체 장소 순서가 최적화 결과와 다르면 잘못된 구간 연결을 차단
def test_adapter_rejects_mismatched_timeline_stop_order() -> None:
    route_option = make_route_option()
    timeline = route_option.timeline.model_copy(
        update={
            "timeline_stops": list(
                reversed(route_option.timeline.timeline_stops)
            )
        }
    )
    mismatched = route_option.model_copy(update={"timeline": timeline})

    with pytest.raises(
        RoutePlannerRouteOptionAdapterError,
        match="전체 장소 순서",
    ):
        RoutePlannerRouteOptionAdapter().to_geometry_queries(
            mismatched,
            ZoneInfo("Asia/Tokyo"),
        )


# Provider 실패를 빈 geometry로 바꾸지 않고 상위 API 계층까지 전파
def test_use_case_propagates_provider_failure() -> None:
    queries = RoutePlannerRouteOptionAdapter().to_geometry_queries(
        make_route_option(),
        ZoneInfo("Asia/Tokyo"),
    )

    with pytest.raises(RuntimeError, match="Google Routes 호출 실패"):
        BuildOptimizedRouteLegGeometries(
            provider=FailingRouteGeometryProvider()
        ).execute(queries)
