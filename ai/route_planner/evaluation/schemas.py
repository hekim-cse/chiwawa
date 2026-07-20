# 정확 경로 및 정확 일자 배정 평가 입력과 결과를 정의하는 DTO
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from ai.route_planner.domain.schemas import (
    TravelMode,
)
from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)


# 평가할 정확 경로 최적화 단계
class RouteEvaluationStage(str, Enum):
    BASELINE = "BASELINE"
    EXACT_DYNAMIC_PROGRAMMING = (
        "EXACT_DYNAMIC_PROGRAMMING"
    )


# 하나의 경로 평가 단계 결과
class RouteStageEvaluationDTO(BaseModel):
    stage: RouteEvaluationStage
    ordered_place_ids: List[str]

    # Matrix 누락 또는 완전 경로 부재 시 None
    total_travel_minutes: Optional[int] = Field(
        default=None,
        ge=0,
    )

    runtime_ms: float = Field(ge=0)

    # 경로 생성에 필요한 누락 구간
    missing_segments: List[str] = Field(
        default_factory=list,
    )


# Baseline과 정확 동적 계획법 경로 결과 비교
class RouteEvaluationResultDTO(BaseModel):
    scenario_id: str
    travel_mode: TravelMode

    baseline: RouteStageEvaluationDTO
    exact_dynamic_programming: (
        RouteStageEvaluationDTO
    )

    improvement_minutes: Optional[int] = None
    improvement_ratio: Optional[float] = None

    evaluated_state_count: int = Field(
        ge=0
    )
    complete_route_found: bool


# JSON에서 이동시간 Matrix 한 구간을 표현하는 DTO
class TravelTimeMatrixEntryDTO(BaseModel):
    origin_place_id: str
    destination_place_id: str
    travel_minutes: int = Field(ge=0)


# Route Evaluation 실행 입력 Scenario
class RouteEvaluationScenarioDTO(BaseModel):
    scenario_id: str
    travel_mode: TravelMode
    day_index: int = Field(ge=1)
    request: TripPlanningRequestDTO
    travel_time_entries: List[
        TravelTimeMatrixEntryDTO
    ]


# 하나의 날짜에 제공되는 일자 배정 Matrix 입력
class DayTravelTimeMatrixDTO(BaseModel):
    day_index: int = Field(ge=1)
    entries: List[
        TravelTimeMatrixEntryDTO
    ]


# 정확 일자 배정 평가 실행 입력 Scenario
class DayAssignmentEvaluationScenarioDTO(
    BaseModel
):
    scenario_id: str
    request: TripPlanningRequestDTO
    travel_time_entries_by_day: List[
        DayTravelTimeMatrixDTO
    ]


# 날짜별 정확 일자 배정 평가 결과
class DayAssignmentEvaluationDayDTO(
    BaseModel
):
    day_index: int = Field(ge=1)
    assigned_poi_ids: List[str]
    assigned_poi_count: int = Field(ge=0)


# 정확 일자 배정 전체 평가 결과
class DayAssignmentEvaluationResultDTO(
    BaseModel
):
    scenario_id: str

    total_travel_minutes: int = Field(
        ge=0
    )
    assigned_poi_count: int = Field(
        ge=0
    )
    unassigned_poi_count: int = Field(
        ge=0
    )
    unassigned_must_visit_count: int = Field(
        ge=0
    )
    preferred_day_violation_count: int = Field(
        ge=0
    )

    complete_assignment: bool
    evaluated_state_count: int = Field(
        ge=0
    )
    runtime_ms: float = Field(ge=0)

    unassigned_poi_ids: List[str]
    days: List[
        DayAssignmentEvaluationDayDTO
    ]
