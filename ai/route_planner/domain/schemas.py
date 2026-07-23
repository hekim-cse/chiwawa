# 데이터 구조 정의 파일
from enum import Enum
import math
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# 이동방식 (도보, 자동차, 대중교통)
class TravelMode(str, Enum):
    WALK = "WALK"
    DRIVE = "DRIVE"
    TRANSIT = "TRANSIT"


# 장소의 위치 정보
class Location(BaseModel):
    name: str
    lat: float = Field(ge=-90, le=90)  # 위도는 -90 ~ 90 범위
    lng: float = Field(ge=-180, le=180)  # 경도는 -180 ~ 180 범위


# Google Maps API에서 반환되는 장소 검색 결과
class PlaceResult(BaseModel):
    place_id: str  # 장소 고유 ID
    name: str
    formatted_address: Optional[str] = None
    location: Location
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    review_count: Optional[int] = Field(default=None, ge=0)


# Google Maps API에서 반환되는 한 구간에서의 이동 시간 정보
class TravelTimeElement(BaseModel):
    origin_name: str  # 출발지 이름
    destination_name: str  # 도착지 이름
    origin_index: int
    destination_index: int
    duration_seconds: Optional[int] = None  # 이동 시간 (초)
    distance_meters: Optional[int] = None  # 이동 거리 (미터)
    status: Optional[str] = None  # API 응답 상태 코드 또는 오류 상태
    # 경로 계산 조건 상태 (예: ROUTE_EXISTS, ROUTE_NOT_FOUND)
    condition: Optional[str] = None

    @property
    def duration_minutes(self) -> Optional[int]:
        if self.duration_seconds is None:
            return None

        # 실제보다 짧은 분 단위 값이 Solver에 전달되지 않도록
        # 남은 초가 있으면 다음 분으로 올림한다.
        return math.ceil(self.duration_seconds / 60)


# 이동 시간 행렬 타입
TravelTimeMatrix = Dict[Tuple[str, str], int]


# 이동 시간 행렬 생성 결과
# matrix: 이동 시간이 정상 계산된 구간
# missing_elements: 이동 시간이 없거나 계산되지 않은 구간
class TravelTimeMatrixResult(BaseModel):
    matrix: TravelTimeMatrix
    missing_elements: List[TravelTimeElement] = Field(default_factory=list)


# 이동 시간 행렬과 장소 정보를 함께 담는 데이터 구조
# Provider의 최종 반환 데이터
# = 경로 최적화 알고리즘에 넘길 입력 데이터
class RouteData(BaseModel):
    locations: List[Location]
    travel_time_matrix_result: TravelTimeMatrixResult

    @property
    def travel_time_matrix(self) -> TravelTimeMatrix:
        return self.travel_time_matrix_result.matrix

    @property
    def missing_travel_time_elements(self) -> List[TravelTimeElement]:
        return self.travel_time_matrix_result.missing_elements
