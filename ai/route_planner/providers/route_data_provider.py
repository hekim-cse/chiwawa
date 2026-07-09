# Places Provider와 Routes Provider를 조합해서 경로 최적화 입력 데이터를 생성하는 Provider
from typing import List

from ai.route_planner.domain.schemas import RouteData, TravelMode
from ai.route_planner.providers.google_places_provider import GooglePlacesProvider
from ai.route_planner.providers.google_routes_provider import GoogleRoutesProvider


# 장소명 목록을 받아 장소 좌표와 이동 시간 행렬을 생성하는 Provider
class RouteDataProvider:
    # RouteDataProvider 생성자
    # places_provider: 장소명 -> 좌표 변환 Provider
    # routes_provider: 좌표 목록 -> 이동 시간 행렬 변환 Provider
    def __init__(
        self,
        places_provider: GooglePlacesProvider | None = None,
        routes_provider: GoogleRoutesProvider | None = None,
    ):
        self.places_provider = places_provider or GooglePlacesProvider()
        self.routes_provider = routes_provider or GoogleRoutesProvider()

    # 장소명 목록과 이동 방식을 받아 경로 최적화 입력 데이터를 생성하는 함수
    # place_names: 사용자가 입력한 장소명 목록
    # travel_mode: 이동 방식 (WALK, DRIVE, TRANSIT)
    # 반환: 장소 좌표 목록 + 이동 시간 행렬 생성 결과
    def build_route_data(
        self,
        place_names: List[str],
        travel_mode: TravelMode = TravelMode.TRANSIT,
    ) -> RouteData:
        if len(place_names) < 2:
            raise ValueError("At least two place names are required.")

        resolved_places = [
            self.places_provider.resolve_place(place_name)
            for place_name in place_names
        ]

        locations = [place.location for place in resolved_places]

        travel_time_matrix_result = self.routes_provider.build_travel_time_matrix_result(
            locations=locations,
            travel_mode=travel_mode,
        )

        return RouteData(
            locations=locations,
            travel_time_matrix_result=travel_time_matrix_result,
        )
