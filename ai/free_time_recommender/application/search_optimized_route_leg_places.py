# 최적화 경로의 모든 구간에서 카테고리별 장소 후보를 검색하는 Use Case
from ai.free_time_recommender.application.search_along_route_places import (
    SearchAlongRoutePlaces,
    SearchAlongRoutePlacesRequest,
)
from ai.free_time_recommender.domain.place_candidate import (
    CategoryRouteLegPlaceCandidates,
    RouteLegPlaceCandidate,
)
from ai.free_time_recommender.domain.route_geometry import (
    OptimizedRouteLegGeometry,
)


class SearchOptimizedRouteLegPlaces:
    """구간별 검색 결과를 카테고리 우선순위로 합치고 중복 제거한다."""

    def __init__(self, *, search_along_route: SearchAlongRoutePlaces) -> None:
        self._search_along_route = search_along_route

    def execute(
        self,
        geometries: tuple[OptimizedRouteLegGeometry, ...],
    ) -> tuple[CategoryRouteLegPlaceCandidates, ...]:
        if not isinstance(geometries, tuple):
            raise TypeError("geometries는 tuple이어야 합니다.")
        if not geometries:
            return ()
        for geometry in geometries:
            if not isinstance(geometry, OptimizedRouteLegGeometry):
                raise TypeError(
                    "geometries는 OptimizedRouteLegGeometry만 포함해야 합니다."
                )

        # 먼저 모든 구간을 검색한 뒤 카테고리 순서로 합쳐, 동일 장소의
        # 대표 카테고리가 서버 카탈로그 우선순위를 따르도록 한다.
        searched_by_leg = tuple(
            (
                geometry,
                self._search_along_route.execute(
                    SearchAlongRoutePlacesRequest(
                        encoded_polyline=geometry.geometry.encoded_polyline
                    )
                ),
            )
            for geometry in geometries
        )
        category_count = len(searched_by_leg[0][1])
        if any(len(groups) != category_count for _, groups in searched_by_leg):
            raise ValueError("구간별 검색 결과의 카테고리 구성이 다릅니다.")

        seen_place_ids: set[str] = set()
        results: list[CategoryRouteLegPlaceCandidates] = []
        for category_index in range(category_count):
            first_group = searched_by_leg[0][1][category_index]
            candidates: list[RouteLegPlaceCandidate] = []
            for geometry, groups in searched_by_leg:
                group = groups[category_index]
                if group.category is not first_group.category:
                    raise ValueError("구간별 검색 결과의 카테고리 순서가 다릅니다.")
                for candidate in group.candidates:
                    if candidate.place_id in seen_place_ids:
                        continue
                    seen_place_ids.add(candidate.place_id)
                    candidates.append(
                        RouteLegPlaceCandidate(
                            candidate=candidate,
                            day_index=geometry.day_index,
                            leg_index=geometry.leg_index,
                            origin_place_id=geometry.origin_place_id,
                            destination_place_id=geometry.destination_place_id,
                        )
                    )
            results.append(
                CategoryRouteLegPlaceCandidates(
                    category=first_group.category,
                    display_name=first_group.display_name,
                    candidates=tuple(candidates),
                )
            )
        return tuple(results)
