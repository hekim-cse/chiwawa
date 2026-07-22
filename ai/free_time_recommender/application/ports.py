# 빈 시간대 추천 Application 계층의 외부 시스템 Port
from typing import Protocol

from ai.free_time_recommender.domain.route_geometry import (
    RouteGeometryQuery,
    RouteLegGeometry,
)


class RouteGeometryProvider(Protocol):
    """두 장소 사이의 검색용 경로 geometry 제공 계약."""

    def get_route_geometry(
        self,
        query: RouteGeometryQuery,
    ) -> RouteLegGeometry:
        ...
