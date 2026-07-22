# Route Planner의 최적화 방문 순서를 구간별 geometry 요청으로 변환
from datetime import datetime
from zoneinfo import ZoneInfo

from ai.free_time_recommender.adapters.errors import (
    RoutePlannerRouteOptionAdapterError,
)
from ai.free_time_recommender.domain.route_geometry import (
    GeoCoordinate,
    OptimizedRouteLegGeometryQuery,
    RouteGeometryQuery,
    RouteTravelMode,
)
from ai.route_planner.domain.schemas import TravelMode
from ai.route_planner.domain.trip_schemas import RouteOptionDTO


class RoutePlannerRouteOptionAdapter:
    """외부 RouteOptionDTO를 내부 구간별 geometry 조건으로 변환한다."""

    TRAVEL_MODE_MAPPING = {
        TravelMode.WALK: RouteTravelMode.WALK,
        TravelMode.DRIVE: RouteTravelMode.DRIVE,
        TravelMode.TRANSIT: RouteTravelMode.TRANSIT,
    }

    def to_geometry_queries(
        self,
        route_option: RouteOptionDTO,
        timezone: ZoneInfo,
    ) -> tuple[OptimizedRouteLegGeometryQuery, ...]:
        """최적화 Stop 순서와 Timeline 출발시각을 구간별로 연결한다."""

        if not isinstance(route_option, RouteOptionDTO):
            raise TypeError("route_option은 RouteOptionDTO여야 합니다.")
        if not isinstance(timezone, ZoneInfo):
            raise TypeError("timezone은 ZoneInfo여야 합니다.")
        if route_option.timeline is None:
            raise RoutePlannerRouteOptionAdapterError(
                "geometry 생성에는 Timeline이 필요합니다."
            )
        if route_option.missing_segments:
            raise RoutePlannerRouteOptionAdapterError(
                "이동시간이 누락된 최적화 경로로 geometry를 생성할 수 없습니다."
            )
        stops = route_option.ordered_stops
        timeline = route_option.timeline
        timeline_stops = timeline.timeline_stops
        if len(stops) < 2:
            raise RoutePlannerRouteOptionAdapterError(
                "최적화 경로에는 두 개 이상의 장소가 필요합니다."
            )
        if len(route_option.route_legs) != len(stops) - 1:
            raise RoutePlannerRouteOptionAdapterError(
                "route_legs 개수가 최적화 장소 순서와 일치하지 않습니다."
            )
        if len(timeline_stops) != len(stops):
            raise RoutePlannerRouteOptionAdapterError(
                "Timeline Stop 개수가 최적화 장소 순서와 일치하지 않습니다."
            )
        if timeline.day_index != route_option.day_index:
            raise RoutePlannerRouteOptionAdapterError(
                "Route Option과 Timeline의 여행 일차가 일치하지 않습니다."
            )
        if timeline.travel_mode is not route_option.travel_mode:
            raise RoutePlannerRouteOptionAdapterError(
                "Route Option과 Timeline의 이동 방식이 일치하지 않습니다."
            )
        if tuple(stop.place_id for stop in timeline_stops) != tuple(
            stop.place_id for stop in stops
        ):
            raise RoutePlannerRouteOptionAdapterError(
                "최적화 장소와 Timeline의 전체 장소 순서가 일치하지 않습니다."
            )

        queries: list[OptimizedRouteLegGeometryQuery] = []
        for leg_index, (origin, destination, route_leg) in enumerate(
            zip(stops, stops[1:], route_option.route_legs)
        ):
            timeline_origin = timeline_stops[leg_index]
            if (
                route_leg.origin_place_id != origin.place_id
                or route_leg.destination_place_id != destination.place_id
            ):
                raise RoutePlannerRouteOptionAdapterError(
                    "장소, 이동 구간, Timeline 순서가 일치하지 않습니다."
                )
            queries.append(
                OptimizedRouteLegGeometryQuery(
                    day_index=route_option.day_index,
                    leg_index=leg_index,
                    origin_place_id=origin.place_id,
                    destination_place_id=destination.place_id,
                    geometry_query=RouteGeometryQuery(
                        origin=GeoCoordinate(origin.lat, origin.lng),
                        destination=GeoCoordinate(
                            destination.lat,
                            destination.lng,
                        ),
                        travel_mode=self.TRAVEL_MODE_MAPPING[
                            route_option.travel_mode
                        ],
                        departure_at=self._parse_datetime(
                            timeline_origin.departure_at,
                            timezone,
                        ),
                    ),
                )
            )
        return tuple(queries)

    @staticmethod
    def _parse_datetime(value: str, timezone: ZoneInfo) -> datetime:
        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except (TypeError, ValueError) as error:
            raise RoutePlannerRouteOptionAdapterError(
                "Timeline 출발시각이 ISO 8601 형식이 아닙니다."
            ) from error
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return parsed.replace(tzinfo=timezone)
        return parsed.astimezone(timezone)
