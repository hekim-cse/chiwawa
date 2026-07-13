# DayPlanDTO의 이동 방식별 RouteOption에 Timeline을 일괄 적용하는 Builder
from typing import List

from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    DayPlanDTO,
    RouteOptionDTO,
)
from ai.route_planner.solvers.timeline_builder import TimelineBuilder


# DayPlanDTO에 포함된 여러 이동 방식의 경로 옵션에 시간표를 생성하는 Builder
class TimelineOptionsBuilder:
    def __init__(
        self,
        timeline_builder: TimelineBuilder | None = None,    # TimelineBuilder 인스턴스를 주입하지 않으면 기본 생성
    ):
        self.timeline_builder = timeline_builder or TimelineBuilder()

    # DayPlanDTO의 모든 RouteOptionDTO에 대해 Timeline을 생성하는 함수
    #
    # 이동 구간이 누락된 RouteOptionDTO는 가짜 시간을 계산하지 않는다.
    # 해당 옵션은 timeline 없이 유지하고 warning만 추가한다.
    def assign_timelines(
        self,
        day_constraint: DayConstraintDTO,   # 날짜와 시작·종료 시간 조건
        day_plan: DayPlanDTO,   # 이동 방식별 경로 옵션이 포함된 day 계획
    ) -> DayPlanDTO:    # route_options가 갱신된 새로운 DayPlanDTO 반환
        self._validate_inputs(
            day_constraint=day_constraint,
            day_plan=day_plan,
        )

        updated_route_options: List[RouteOptionDTO] = []

        for route_option in day_plan.route_options:
            updated_route_option = self._assign_route_option_timeline(
                day_constraint=day_constraint,
                day_plan=day_plan,
                route_option=route_option,
            )
            updated_route_options.append(updated_route_option)

        # 원본 DayPlanDTO를 직접 수정하지 않고 갱신된 새 DTO 반환
        return day_plan.model_copy(
            update={
                "route_options": updated_route_options,
            }
        )

    # 하나의 RouteOptionDTO에 Timeline을 생성하거나 누락 상태를 반영하는 함수
    def _assign_route_option_timeline(
        self,
        day_constraint: DayConstraintDTO,
        day_plan: DayPlanDTO,
        route_option: RouteOptionDTO,
    ) -> RouteOptionDTO:
        if route_option.missing_segments:
            warning = (
                f"{route_option.travel_mode.value} 경로에 누락 구간이 있어 "
                "시간표를 생성하지 않았습니다."
            )

            warnings = self._merge_warnings(
                existing_warnings=route_option.warnings,
                additional_warnings=[warning],
            )

            return route_option.model_copy(
                update={
                    "timeline": None,
                    "warnings": warnings,
                }
            )

        return self.timeline_builder.assign_timeline(
            day_constraint=day_constraint,
            day_plan=day_plan,
            route_option=route_option,
        )

    # DayConstraintDTO와 DayPlanDTO의 기본 관계를 검증하는 함수
    def _validate_inputs(
        self,
        day_constraint: DayConstraintDTO,
        day_plan: DayPlanDTO,
    ) -> None:
        if day_constraint.day_index != day_plan.day_index:  # day_index가 서로 다르면 ValueError 발생
            raise ValueError(
                "day_index must match between "
                "DayConstraintDTO and DayPlanDTO."
            )

        if day_constraint.date != day_plan.date:    # date가 서로 다르면 ValueError 발생
            raise ValueError(
                "date must match between "
                "DayConstraintDTO and DayPlanDTO."
            )

        if not day_plan.route_options:  # route_options가 비어있으면 ValueError 발생
            raise ValueError(
                "DayPlanDTO.route_options must not be empty."
            )

    # 기존 warning과 추가 warning을 순서를 유지하면서 중복 없이 병합하는 함수
    def _merge_warnings(
        self,
        existing_warnings: List[str],
        additional_warnings: List[str],
    ) -> List[str]:
        merged_warnings: List[str] = []

        for warning in [
            *existing_warnings,
            *additional_warnings,
        ]:
            if warning not in merged_warnings:
                merged_warnings.append(warning)

        return merged_warnings
