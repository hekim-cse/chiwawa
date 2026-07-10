# 백엔드와 AI 일정 최적화 모듈이 주고받는 DTO 정의 파일
from enum import Enum   # 정해진 값만 허용하고 싶을 때 사용
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from ai.route_planner.domain.schemas import TravelMode


# 장소 카테고리
class PoiCategory(str, Enum):
    TOURIST_ATTRACTION = "TOURIST_ATTRACTION"
    RESTAURANT = "RESTAURANT"
    CAFE = "CAFE"
    SHOPPING = "SHOPPING"
    ACTIVITY = "ACTIVITY"
    HOTEL = "HOTEL"
    ETC = "ETC"


# AI 일정 생성 상태
class TripPlanningStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


# 출발지, 도착지, POI 위치 정보를 표현하는 공통 장소 DTO
class PlaceDTO(BaseModel):
    place_id: str
    name: str
    lat: float
    lng: float


# 사용자가 가고 싶다고 확정한 장소 DTO
class PoiDTO(BaseModel):
    poi_id: str
    place_id: str
    name: str
    lat: float
    lng: float
    category: PoiCategory = PoiCategory.ETC
    estimated_stay_minutes: int = Field(gt=0)
    priority: int = Field(default=3, ge=1, le=5)
    must_visit: bool = True
    preferred_day_index: Optional[int] = Field(default=None, ge=1)


# 각 여행 일자의 출발지, 도착지, 시간 조건 DTO
class DayConstraintDTO(BaseModel):
    day_index: int = Field(ge=1)
    date: str
    start_place: PlaceDTO
    start_time: str
    end_place: PlaceDTO
    end_time: str
    max_place_count: Optional[int] = Field(default=None, gt=0)


# 백엔드에서 AI로 전달하는 여행 일정 최적화 요청 DTO
class TripPlanningRequestDTO(BaseModel):
    trip_id: str
    timezone: str = "Asia/Tokyo"
    days: List[DayConstraintDTO]
    pois: List[PoiDTO]

    # 여행 일정 생성 요청의 기본 조건을 검증하는 함수
    # days와 pois가 비어 있으면 일정 분배를 수행할 수 없으므로 예외 발생
    @model_validator(mode="after")
    def validate_trip_planning_request(self):
        if not self.days:
            raise ValueError("days must not be empty.")

        if not self.pois:
            raise ValueError("pois must not be empty.")

        day_indexes = [day.day_index for day in self.days]
        if len(day_indexes) != len(set(day_indexes)):
            raise ValueError("day_index values must be unique.")

        valid_day_indexes = set(day_indexes)
        for poi in self.pois:
            if (
                poi.preferred_day_index is not None
                and poi.preferred_day_index not in valid_day_indexes
            ):
                raise ValueError(
                    f"preferred_day_index must exist in days. "
                    f"poi_id={poi.poi_id}, preferred_day_index={poi.preferred_day_index}"
                )

        return self


# 경로 정류장 타입
class RouteStopType(str, Enum):
    START = "START"
    POI = "POI"
    END = "END"


# 경로 내 개별 정류장 DTO
class RouteStopDTO(BaseModel):
    stop_type: RouteStopType
    place_id: str
    name: str
    lat: float
    lng: float


# 경로 내 한 이동 구간 DTO
class RouteLegDTO(BaseModel):
    origin_place_id: str
    destination_place_id: str
    travel_minutes: int


# day별 이동 방식 경로 옵션 DTO
class RouteOptionDTO(BaseModel):
    day_index: int = Field(ge=1)    # 몇 번째 day의 경로 옵션인지
    travel_mode: TravelMode # 이동 방식 (DRIVE, WALK, TRANSIT 등)
    total_travel_minutes: int = Field(ge=0)
    ordered_stops: List[RouteStopDTO]   # 실제 방문 순서
    route_legs: List[RouteLegDTO]   # 각 이동 구간 정보
    missing_segments: List[str] = Field(default_factory=list)   # 이동 시간 정보가 부족한 구간(place_id) 리스트
    warnings: List[str] = Field(default_factory=list)   # 경로 옵션 생성 시 발생한 경고 메시지 리스트


# day별 장소 배정 결과 DTO
class DayPlanDTO(BaseModel):
    day_index: int = Field(ge=1)
    date: str
    start_place: PlaceDTO
    end_place: PlaceDTO
    assigned_pois: List[PoiDTO]
    estimated_total_stay_minutes: int = Field(ge=0)
    assignment_reason: str
    route_options: List[RouteOptionDTO] = Field(default_factory=list)


# 배정되지 못한 장소와 사유를 표현하는 DTO
class UnassignedPoiDTO(BaseModel):
    poi: PoiDTO
    reason: str




# AI가 백엔드에 반환하는 여행 일정 최적화 응답 DTO
class TripPlanningResponseDTO(BaseModel):
    trip_id: str
    status: TripPlanningStatus
    day_plans: List[DayPlanDTO]
    unassigned_pois: List[UnassignedPoiDTO] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
