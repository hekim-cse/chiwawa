# 정확 일자 배정 결과를 여행 일정 도메인 DTO로 변환하는 Day Assignment 어댑터
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Optional, Tuple

from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    DayPlanDTO,
    PoiDTO,
    TripPlanningRequestDTO,
    TripPlanningResponseDTO,
    TripPlanningStatus,
    UnassignedPoiDTO,
)
from ai.route_planner.solvers.exact_day_assignment_solver import (
    ExactDayAssignmentResult,
    ExactDayAssignmentSolver,
    TravelTimeMatricesByDay,
)


# Day Assignment 응답 조립과 경고 정책 설정
@dataclass(frozen=True)
class DayAssignmentSolverConfig:
    warn_when_stay_time_exceeds_available_time: bool = True


# 정확 일자 배정 엔진을 호출하고 여행 일정 응답 DTO를 생성하는 어댑터
class DayAssignmentSolver:
    def __init__(
        self,
        exact_day_assignment_solver: Optional[
            ExactDayAssignmentSolver
        ] = None,
        config: Optional[
            DayAssignmentSolverConfig
        ] = None,
    ) -> None:
        self._exact_day_assignment_solver = (
            exact_day_assignment_solver
            or ExactDayAssignmentSolver()
        )
        self._config = (
            config
            or DayAssignmentSolverConfig()
        )

    # 요청과 날짜별 Matrix를 받아 정확 일자 배정 응답 생성
    def assign_pois_to_days(
        self,
        request: TripPlanningRequestDTO,
        travel_time_matrices_by_day: (
            TravelTimeMatricesByDay
        ),
    ) -> TripPlanningResponseDTO:
        exact_result = (
            self._exact_day_assignment_solver.solve(
                days=request.days,
                pois=request.pois,
                travel_time_matrices_by_day=(
                    travel_time_matrices_by_day
                ),
            )
        )

        poi_by_id = self._build_poi_by_id(
            request.pois
        )

        day_plans, warnings = (
            self._build_day_plans(
                days=request.days,
                poi_by_id=poi_by_id,
                exact_result=exact_result,
            )
        )

        unassigned_pois = (
            self._build_unassigned_pois(
                poi_by_id=poi_by_id,
                unassigned_poi_ids=(
                    exact_result
                    .unassigned_poi_ids
                ),
            )
        )

        return TripPlanningResponseDTO(
            trip_id=request.trip_id,
            status=self._resolve_status(
                unassigned_pois=(
                    unassigned_pois
                ),
            ),
            day_plans=day_plans,
            unassigned_pois=unassigned_pois,
            warnings=warnings,
        )

    # POI 식별자별 DTO 조회 Map 생성
    def _build_poi_by_id(
        self,
        pois: list[PoiDTO],
    ) -> Mapping[str, PoiDTO]:
        poi_by_id = {
            poi.poi_id: poi
            for poi in pois
        }

        if len(poi_by_id) != len(pois):
            raise ValueError(
                "poi_id는 중복될 수 없습니다."
            )

        return poi_by_id

    # 정확 배정 결과를 날짜별 DayPlanDTO로 변환
    def _build_day_plans(
        self,
        days: list[DayConstraintDTO],
        poi_by_id: Mapping[str, PoiDTO],
        exact_result: ExactDayAssignmentResult,
    ) -> Tuple[list[DayPlanDTO], list[str]]:
        day_plans: list[DayPlanDTO] = []
        warnings: list[str] = []

        for day in sorted(
            days,
            key=lambda item: item.day_index,
        ):
            assigned_poi_ids = (
                exact_result
                .assigned_poi_ids_by_day
                .get(
                    day.day_index,
                    (),
                )
            )

            assigned_pois = [
                self._get_poi_or_raise(
                    poi_by_id=poi_by_id,
                    poi_id=poi_id,
                )
                for poi_id in assigned_poi_ids
            ]

            estimated_total_stay_minutes = (
                sum(
                    poi.estimated_stay_minutes
                    for poi in assigned_pois
                )
            )

            self._append_stay_time_warning(
                day=day,
                estimated_total_stay_minutes=(
                    estimated_total_stay_minutes
                ),
                warnings=warnings,
            )

            day_plans.append(
                DayPlanDTO(
                    day_index=day.day_index,
                    date=day.date,
                    start_place=day.start_place,
                    end_place=day.end_place,
                    assigned_pois=assigned_pois,
                    estimated_total_stay_minutes=(
                        estimated_total_stay_minutes
                    ),
                    assignment_reason=(
                        "정확 일자 배정 최적화 결과"
                    ),
                )
            )

        self._validate_assignment_result(
            day_plans=day_plans,
            exact_result=exact_result,
        )

        return day_plans, warnings

    # 미배정 POI DTO 목록 생성
    def _build_unassigned_pois(
        self,
        poi_by_id: Mapping[str, PoiDTO],
        unassigned_poi_ids: Tuple[str, ...],
    ) -> list[UnassignedPoiDTO]:
        return [
            UnassignedPoiDTO(
                poi=self._get_poi_or_raise(
                    poi_by_id=poi_by_id,
                    poi_id=poi_id,
                ),
                reason=(
                    "날짜별 수용량 또는 완전 경로 "
                    "제약으로 정확 배정되지 못함"
                ),
            )
            for poi_id in unassigned_poi_ids
        ]

    # POI 식별자에 해당하는 DTO 조회
    def _get_poi_or_raise(
        self,
        poi_by_id: Mapping[str, PoiDTO],
        poi_id: str,
    ) -> PoiDTO:
        poi = poi_by_id.get(poi_id)

        if poi is None:
            raise ValueError(
                "정확 일자 배정 결과에 "
                "알 수 없는 poi_id가 포함되었습니다: "
                f"{poi_id}"
            )

        return poi

    # 체류시간이 날짜 사용 가능 시간을 초과하는 경우 경고 추가
    def _append_stay_time_warning(
        self,
        day: DayConstraintDTO,
        estimated_total_stay_minutes: int,
        warnings: list[str],
    ) -> None:
        if not (
            self._config
            .warn_when_stay_time_exceeds_available_time
        ):
            return

        available_minutes = (
            self._calculate_available_minutes(
                day
            )
        )

        if (
            estimated_total_stay_minutes
            <= available_minutes
        ):
            return

        warnings.append(
            f"day_index={day.day_index}의 "
            "예상 체류시간이 사용 가능 시간을 "
            "초과했습니다: "
            f"stay={estimated_total_stay_minutes}, "
            f"available={available_minutes}"
        )

    # 날짜 시작시간과 종료시간 사이의 사용 가능 분 계산
    def _calculate_available_minutes(
        self,
        day: DayConstraintDTO,
    ) -> int:
        start_time = datetime.strptime(
            day.start_time,
            "%H:%M",
        )
        end_time = datetime.strptime(
            day.end_time,
            "%H:%M",
        )

        available_minutes = int(
            (
                end_time - start_time
            ).total_seconds()
            // 60
        )

        if available_minutes < 0:
            raise ValueError(
                "end_time은 start_time보다 "
                "빠를 수 없습니다: "
                f"day_index={day.day_index}"
            )

        return available_minutes

    # 정확 배정 결과와 생성된 DayPlanDTO의 무결성 검증
    def _validate_assignment_result(
        self,
        day_plans: list[DayPlanDTO],
        exact_result: ExactDayAssignmentResult,
    ) -> None:
        assigned_poi_ids = [
            poi.poi_id
            for day_plan in day_plans
            for poi in day_plan.assigned_pois
        ]

        if len(
            assigned_poi_ids
        ) != len(
            set(assigned_poi_ids)
        ):
            raise ValueError(
                "POI가 여러 날짜에 중복 배정되었습니다."
            )

        expected_assigned_poi_ids = {
            poi_id
            for poi_ids in (
                exact_result
                .assigned_poi_ids_by_day
                .values()
            )
            for poi_id in poi_ids
        }

        if set(
            assigned_poi_ids
        ) != expected_assigned_poi_ids:
            raise ValueError(
                "정확 일자 배정 결과와 "
                "DayPlanDTO의 POI 집합이 다릅니다."
            )

        assigned_and_unassigned = (
            set(assigned_poi_ids)
            | set(
                exact_result
                .unassigned_poi_ids
            )
        )

        if len(
            assigned_and_unassigned
        ) != (
            len(assigned_poi_ids)
            + len(
                exact_result
                .unassigned_poi_ids
            )
        ):
            raise ValueError(
                "동일한 POI가 배정 및 미배정 "
                "결과에 동시에 포함되었습니다."
            )

    # 미배정 POI 존재 여부에 따라 응답 상태 결정
    def _resolve_status(
        self,
        unassigned_pois: list[
            UnassignedPoiDTO
        ],
    ) -> TripPlanningStatus:
        if unassigned_pois:
            return (
                TripPlanningStatus
                .PARTIAL_SUCCESS
            )

        return TripPlanningStatus.SUCCESS
