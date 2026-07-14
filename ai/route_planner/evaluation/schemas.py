# 경로 최적화 알고리즘의 단계별 평가 결과 DTO
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from ai.route_planner.domain.schemas import TravelMode
from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)


# 평가할 경로 최적화 단계
class RouteEvaluationStage(str, Enum):
    BASELINE = "BASELINE"
    CHEAPEST_INSERTION = "CHEAPEST_INSERTION"
    RELOCATE = "RELOCATE"
    TWO_OPT = "TWO_OPT"
    FINAL_LOCAL_SEARCH = "FINAL_LOCAL_SEARCH"


# 하나의 최적화 단계에 대한 평가 결과
class RouteStageEvaluationDTO(BaseModel):
    stage: RouteEvaluationStage
    ordered_place_ids: List[str]

    # Matrix 누락으로 전체 비용을 계산할 수 없으면 None
    total_travel_minutes: Optional[int] = Field(
        default=None,
        ge=0,
    )

    # 바로 이전 단계와 비교한 개선 결과
    improvement_minutes_from_previous: Optional[int] = None 
    improvement_ratio_from_previous: Optional[float] = None

    # 입력 순서 Baseline과 비교한 전체 개선 결과
    improvement_minutes_from_baseline: Optional[int] = None
    improvement_ratio_from_baseline: Optional[float] = None

    # 해당 단계 실행 시간
    runtime_ms: float = Field(ge=0)

    # 최종 경로 비용 계산에 필요한 Matrix 누락 구간
    missing_segments: List[str] = Field(
        default_factory=list,
    )


# 하나의 평가 Scenario에 대한 전체 결과
class RouteEvaluationResultDTO(BaseModel):
    scenario_id: str
    travel_mode: TravelMode

    baseline: RouteStageEvaluationDTO
    cheapest_insertion: RouteStageEvaluationDTO
    relocate: RouteStageEvaluationDTO
    two_opt: RouteStageEvaluationDTO
    final_local_search: RouteStageEvaluationDTO

    # Cheapest Insertion 과정에서 경로에 넣지 못한 POI
    uninserted_place_ids: List[str] = Field(
        default_factory=list,
    )


# JSON에서 이동 시간 행렬 한 구간을 표현하는 DTO
# JSON 객체의 key에는 tuple을 사용할 수 없으므로 구간 목록 형태로 저장
class TravelTimeMatrixEntryDTO(BaseModel):
    origin_place_id: str
    destination_place_id: str
    travel_minutes: int = Field(ge=0)


# Route Evaluation 실행에 필요한 입력 Scenario DTO
class RouteEvaluationScenarioDTO(BaseModel):
    scenario_id: str
    travel_mode: TravelMode
    day_index: int = Field(ge=1)
    request: TripPlanningRequestDTO
    travel_time_entries: List[TravelTimeMatrixEntryDTO]
