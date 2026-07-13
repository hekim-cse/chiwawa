# Day 시간 조건과 Route Option을 기반으로 실제 방문 시간표를 생성하는 Builder
from datetime import datetime, timedelta
from typing import Dict, List

from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    DayPlanDTO,
    RouteOptionDTO,
    RouteStopType,
    TimelineDTO,
    TimelineStopDTO,
)


# RouteOptionDTO의 방문 순서와 이동 시간을 실제 시간표로 변환하는 Builder
class TimelineBuilder:
    # Day 시간 조건, POI 체류 시간, 경로 옵션을 기반으로 시간표를 생성하는 함수
    def assign_timeline(
        self,
        day_constraint: DayConstraintDTO,   # 날짜, 시작 시간, 종료 시간 조건
        day_plan: DayPlanDTO,   # day에 배정된 POI와 체류 시간 정보
        route_option: RouteOptionDTO,   # 방문 순서와 구간별 이동 시간 정보
    ) -> RouteOptionDTO:    # timeline이 주입된 새로운 RouteOptionDTO 반환
        self._validate_inputs(
            day_constraint=day_constraint,
            day_plan=day_plan,
            route_option=route_option,
        )

        # 시작 시간과 종료 시간을 datetime으로 변환
        planned_start_at = self._parse_datetime(
            date=day_constraint.date,
            time=day_constraint.start_time,
        )
        planned_end_at = self._parse_datetime(
            date=day_constraint.date,
            time=day_constraint.end_time,
        )

        if planned_end_at <= planned_start_at:
            raise ValueError(
                "end_time must be later than start_time on the same date."
            )

        stay_minutes_by_place_id = {
            poi.place_id: poi.estimated_stay_minutes
            for poi in day_plan.assigned_pois
        }

        # 방문 순서와 구간별 이동 시간을 기반으로 시간표 정류장 목록 생성
        timeline_stops = self._build_timeline_stops(
            route_option=route_option,
            planned_start_at=planned_start_at,
            stay_minutes_by_place_id=stay_minutes_by_place_id,
        )

        # 실제 종료 시간과 총 체류 시간을 계산하고, 예상 종료 시간 초과 여부를 판단
        actual_end_at = self._parse_iso_datetime(
            timeline_stops[-1].departure_at
        )
        total_stay_minutes = sum(
            stop.stay_minutes
            for stop in timeline_stops
        )
        exceeds_planned_end = actual_end_at > planned_end_at

        warnings = list(route_option.warnings)

        if exceeds_planned_end:
            exceeded_minutes = int(
                (actual_end_at - planned_end_at).total_seconds() // 60
            )
            warnings.append(
                "계산된 일정이 day 종료 시간을 "
                f"{exceeded_minutes}분 초과합니다."
            )

        timeline = TimelineDTO(
            day_index=day_plan.day_index,
            travel_mode=route_option.travel_mode,
            planned_start_at=self._format_datetime(planned_start_at),
            planned_end_at=self._format_datetime(planned_end_at),
            actual_end_at=self._format_datetime(actual_end_at),
            total_travel_minutes=route_option.total_travel_minutes,
            total_stay_minutes=total_stay_minutes,
            timeline_stops=timeline_stops,
            exceeds_planned_end=exceeds_planned_end,
            warnings=warnings,
        )

        # 원본 RouteOptionDTO를 직접 수정하지 않고 timeline이 적용된 새 DTO 반환
        return route_option.model_copy(
            update={
                "timeline": timeline,
            }
        )

    # 방문 순서와 구간별 이동 시간을 시간표 정류장 목록으로 변환하는 함수
    def _build_timeline_stops(
        self,
        route_option: RouteOptionDTO,
        planned_start_at: datetime,
        stay_minutes_by_place_id: Dict[str, int],
    ) -> List[TimelineStopDTO]:
        first_stop = route_option.ordered_stops[0]

        timeline_stops = [
            TimelineStopDTO(
                stop_type=first_stop.stop_type,
                place_id=first_stop.place_id,
                name=first_stop.name,
                arrival_at=self._format_datetime(planned_start_at),
                departure_at=self._format_datetime(planned_start_at),
                stay_minutes=0,
            )
        ]

        current_at = planned_start_at

        for leg, destination_stop in zip(
            route_option.route_legs,
            route_option.ordered_stops[1:],
        ):
            current_at += timedelta(
                minutes=leg.travel_minutes
            )
            arrival_at = current_at

            stay_minutes = self._get_stay_minutes(
                stop_type=destination_stop.stop_type,
                place_id=destination_stop.place_id,
                stay_minutes_by_place_id=stay_minutes_by_place_id,
            )

            departure_at = arrival_at + timedelta(
                minutes=stay_minutes
            )
            current_at = departure_at

            timeline_stops.append(
                TimelineStopDTO(
                    stop_type=destination_stop.stop_type,
                    place_id=destination_stop.place_id,
                    name=destination_stop.name,
                    arrival_at=self._format_datetime(arrival_at),
                    departure_at=self._format_datetime(departure_at),
                    stay_minutes=stay_minutes,
                )
            )

        return timeline_stops

    # 정류장 타입에 따라 체류 시간을 반환하는 함수
    # START와 END는 체류 시간 0분, POI는 DayPlanDTO의 예상 체류 시간 사용
    def _get_stay_minutes(
        self,
        stop_type: RouteStopType,
        place_id: str,
        stay_minutes_by_place_id: Dict[str, int],
    ) -> int:
        if stop_type != RouteStopType.POI:
            return 0

        if place_id not in stay_minutes_by_place_id:
            raise ValueError(
                "POI stay time not found for place_id: "
                f"{place_id}"
            )

        return stay_minutes_by_place_id[place_id]

    # Timeline Builder 입력 DTO들의 구조와 관계를 검증하는 함수
    def _validate_inputs(
        self,
        day_constraint: DayConstraintDTO,
        day_plan: DayPlanDTO,
        route_option: RouteOptionDTO,
    ) -> None:
        if not (
            day_constraint.day_index
            == day_plan.day_index
            == route_option.day_index
        ):
            raise ValueError(
                "day_index must match across "
                "DayConstraintDTO, DayPlanDTO, and RouteOptionDTO."
            )

        if day_constraint.date != day_plan.date:
            raise ValueError(
                "date must match between "
                "DayConstraintDTO and DayPlanDTO."
            )

        if route_option.missing_segments:
            raise ValueError(
                "Timeline cannot be built from a route option "
                "with missing segments."
            )

        if len(route_option.ordered_stops) < 2:
            raise ValueError(
                "Route option must contain at least START and END stops."
            )

        if route_option.ordered_stops[0].stop_type != RouteStopType.START:
            raise ValueError(
                "The first ordered stop must be START."
            )

        if route_option.ordered_stops[-1].stop_type != RouteStopType.END:
            raise ValueError(
                "The last ordered stop must be END."
            )

        if (
            route_option.ordered_stops[0].place_id
            != day_constraint.start_place.place_id
        ):
            raise ValueError(
                "Route START place must match DayConstraintDTO.start_place."
            )

        if (
            route_option.ordered_stops[-1].place_id
            != day_constraint.end_place.place_id
        ):
            raise ValueError(
                "Route END place must match DayConstraintDTO.end_place."
            )

        expected_leg_count = len(route_option.ordered_stops) - 1

        if len(route_option.route_legs) != expected_leg_count:
            raise ValueError(
                "route_legs count must equal ordered_stops count minus one."
            )

        for index, leg in enumerate(route_option.route_legs):
            origin_stop = route_option.ordered_stops[index]
            destination_stop = route_option.ordered_stops[index + 1]

            if (
                leg.origin_place_id != origin_stop.place_id
                or leg.destination_place_id != destination_stop.place_id
            ):
                raise ValueError(
                    "Route leg order must match ordered_stops."
                )

        calculated_total_travel_minutes = sum(
            leg.travel_minutes
            for leg in route_option.route_legs
        )

        if (
            calculated_total_travel_minutes
            != route_option.total_travel_minutes
        ):
            raise ValueError(
                "Route leg travel time sum must match "
                "total_travel_minutes."
            )

    # 날짜와 HH:MM 문자열을 datetime으로 변환하는 함수
    # 예외: 날짜 또는 시간 형식이 올바르지 않으면 ValueError 발생
    def _parse_datetime(
        self,
        date: str,
        time: str,
    ) -> datetime:
        try:
            return datetime.strptime(
                f"{date} {time}",
                "%Y-%m-%d %H:%M",
            )
        except ValueError as error:
            raise ValueError(
                "date and time must use YYYY-MM-DD and HH:MM formats."
            ) from error

    # ISO 형식 문자열을 datetime으로 변환하는 함수
    def _parse_iso_datetime(
        self,
        value: str,
    ) -> datetime:
        return datetime.fromisoformat(value)

    # datetime을 분 단위 ISO 문자열로 변환하는 함수
    def _format_datetime(
        self,
        value: datetime,
    ) -> str:
        return value.isoformat(
            timespec="minutes"
        )
