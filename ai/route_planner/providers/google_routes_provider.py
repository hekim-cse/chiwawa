# Google Routes API를 호출해서 “장소 좌표 목록”을 “이동 시간 행렬”로 변환하는 Provider
import re
from typing import List, Optional

import httpx

from ai.route_planner.domain.schemas import (
    Location,
    TravelMode,
    TravelTimeElement,
    TravelTimeMatrix,
    TravelTimeMatrixResult,
)
from ai.route_planner.providers.env import get_google_maps_api_key


# Google Routes API를 호출해서 장소 간 이동 시간/거리 정보를 계산하는 Provider
class GoogleRoutesProvider:
    BASE_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"

    # GoogleRoutesProvider 생성자
    # api_key: Google Routes API 키 (없으면 환경변수에서 가져옴)
    # timeout_seconds: API 호출 타임아웃 (초)
    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 20.0):
        self.api_key = api_key or get_google_maps_api_key()
        self.timeout_seconds = timeout_seconds

    # 장소 좌표 목록과 이동 방식을 받아 이동 시간 행렬 생성 결과를 반환하는 함수
    # locations: 이동 시간을 계산할 장소 좌표 목록
    # travel_mode: 이동 방식 (WALK, DRIVE, TRANSIT)
    # 반환: 이동 시간 행렬 + 누락 구간 목록
    def build_travel_time_matrix_result(
        self,
        locations: List[Location],
        travel_mode: TravelMode = TravelMode.TRANSIT,
    ) -> TravelTimeMatrixResult:
        elements = self.compute_route_matrix(
            locations=locations,
            travel_mode=travel_mode,
        )

        matrix: TravelTimeMatrix = {}
        missing_elements: List[TravelTimeElement] = []

        for element in elements:
            # duration이 없으면 조용히 버리지 않고 누락 구간 목록에 저장
            if element.duration_minutes is None:
                missing_elements.append(element)
                continue

            matrix[(element.origin_name, element.destination_name)] = element.duration_minutes

        return TravelTimeMatrixResult(
            matrix=matrix,
            missing_elements=missing_elements,
        )

    # 기존 호출부와의 호환을 위한 함수
    # 반환: 이동 시간이 정상 계산된 구간만 담은 이동 시간 행렬
    def build_travel_time_matrix(
        self,
        locations: List[Location],
        travel_mode: TravelMode = TravelMode.TRANSIT,
    ) -> TravelTimeMatrix:
        result = self.build_travel_time_matrix_result(
            locations=locations,
            travel_mode=travel_mode,
        )

        return result.matrix

    # Google Routes API의 Compute Route Matrix를 호출하는 핵심 함수
    # locations: 출발지/도착지로 모두 사용할 장소 좌표 목록
    # travel_mode: 이동 방식 (WALK, DRIVE, TRANSIT)
    # 반환: Google Routes API 응답을 TravelTimeElement 리스트로 변환한 결과
    # 예외: 장소가 2개 미만이거나, 요청 가능한 행렬 크기를 초과하면 ValueError 발생
    def compute_route_matrix(
        self,
        locations: List[Location],
        travel_mode: TravelMode = TravelMode.TRANSIT,
    ) -> List[TravelTimeElement]:
        if len(locations) < 2:
            raise ValueError("At least two locations are required.")

        # Google Routes API의 route matrix 요청 크기 제한을 넘지 않도록 사전 검증
        # origins 개수 × destinations 개수 = route matrix element 개수
        element_count = len(locations) * len(locations)
        if element_count > 625:
            raise ValueError(
                f"Too many matrix elements: {element_count}. "
                "Reduce locations or split requests."
            )

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "originIndex,"
                "destinationIndex,"
                "duration,"
                "distanceMeters,"
                "status,"
                "condition"
            ),
        }

        payload = {
            "origins": [self._to_route_matrix_location(location) for location in locations],
            "destinations": [self._to_route_matrix_location(location) for location in locations],
            "travelMode": travel_mode.value,
        }

        # Google Routes API에 POST 요청 전송
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(self.BASE_URL, headers=headers, json=payload)

        # API 요청 실패 시 상태 코드와 응답 본문을 함께 출력
        if response.status_code >= 400:
            raise RuntimeError(
                "Google Routes API request failed: "
                f"status={response.status_code}, body={response.text}"
            )

        raw_elements = response.json()
        return [self._parse_element(element, locations) for element in raw_elements]

    # 우리 서비스의 Location 모델을 Google Routes API 요청 형식으로 변환하는 함수
    # 반환: Google Routes API의 waypoint/location/latLng 형식 dict
    def _to_route_matrix_location(self, location: Location) -> dict:
        return {
            "waypoint": {
                "location": {
                    "latLng": {
                        "latitude": location.lat,
                        "longitude": location.lng,
                    }
                }
            }
        }

    # Google Routes API 응답 element 하나를 TravelTimeElement 모델로 변환하는 함수
    # element: Google Routes API가 반환한 route matrix element
    # locations: originIndex/destinationIndex를 실제 장소명으로 매핑하기 위한 장소 목록
    # 반환: TravelTimeElement 객체
    def _parse_element(
        self,
        element: dict,
        locations: List[Location],
    ) -> TravelTimeElement:
        origin_index = element["originIndex"]
        destination_index = element["destinationIndex"]

        return TravelTimeElement(
            origin_name=locations[origin_index].name,
            destination_name=locations[destination_index].name,
            origin_index=origin_index,
            destination_index=destination_index,
            duration_seconds=self._parse_duration_seconds(element.get("duration")),
            distance_meters=element.get("distanceMeters"),
            status=(
                element.get("status", {}).get("code")
                if isinstance(element.get("status"), dict)
                else None
            ),
            condition=element.get("condition"),
        )

    # Google Routes API의 duration 문자열을 초 단위 정수로 변환하는 함수
    # 예: "420s" -> 420
    # duration이 없으면 None 반환
    # 예외: 예상하지 못한 duration 형식이면 ValueError 발생
    def _parse_duration_seconds(self, duration: Optional[str]) -> Optional[int]:
        if duration is None:
            return None

        match = re.fullmatch(r"(\d+)s", duration)
        if not match:
            raise ValueError(f"Invalid duration format: {duration}")

        return int(match.group(1))
