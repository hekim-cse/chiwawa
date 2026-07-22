# 최적화 방문 순서의 각 이동 구간 geometry 생성 Use Case
from ai.free_time_recommender.application.ports import RouteGeometryProvider
from ai.free_time_recommender.domain.route_geometry import (
    OptimizedRouteLegGeometry,
    OptimizedRouteLegGeometryQuery,
)


class BuildOptimizedRouteLegGeometries:
    """구간 순서를 유지하며 Provider geometry 결과를 결합한다."""

    def __init__(self, *, provider: RouteGeometryProvider) -> None:
        self._provider = provider

    def execute(
        self,
        queries: tuple[OptimizedRouteLegGeometryQuery, ...],
    ) -> tuple[OptimizedRouteLegGeometry, ...]:
        """각 구간을 조회하고 원래 구간 식별자와 결과를 결합한다.

        Provider 오류는 여기서 숨기거나 빈 결과로 바꾸지 않는다. 호출자가
        외부 경로 조회 실패를 명시적으로 API 오류로 변환할 수 있도록 그대로
        전파한다.
        """

        if not isinstance(queries, tuple):
            raise TypeError("queries는 tuple이어야 합니다.")

        results: list[OptimizedRouteLegGeometry] = []
        for query in queries:
            if not isinstance(query, OptimizedRouteLegGeometryQuery):
                raise TypeError(
                    "queries는 OptimizedRouteLegGeometryQuery만 "
                    "포함해야 합니다."
                )
            # Provider에는 외부 DTO가 아니라 순수 geometry 조건만 전달한다.
            geometry = self._provider.get_route_geometry(
                query.geometry_query
            )

            # 비동기·병렬 조회로 바꾸더라도 leg_index가 결합 기준이 된다.
            results.append(
                OptimizedRouteLegGeometry(
                    day_index=query.day_index,
                    leg_index=query.leg_index,
                    origin_place_id=query.origin_place_id,
                    destination_place_id=query.destination_place_id,
                    geometry=geometry,
                )
            )
        return tuple(results)
