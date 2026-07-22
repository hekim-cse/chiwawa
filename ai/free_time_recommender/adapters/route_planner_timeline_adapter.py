# Route Planner의 TimelineDTO를
# 빈 시간 추천 도메인의 DayAvailability로 변환하는 어댑터
from dataclasses import dataclass, replace
from datetime import datetime
from zoneinfo import ZoneInfo

from ai.free_time_recommender.adapters.errors import (
    RoutePlannerTimelineAdapterError,
)
from ai.free_time_recommender.domain.models import (
    BusyTimeInterval,
    DayAvailability,
    ScheduleBoundary,
)
from ai.free_time_recommender.domain.recommendation_budget import (
    RecommendationTimeWindow,
)
from ai.free_time_recommender.domain.route_insertion import (
    RouteLegInsertionWindow,
)
from ai.route_planner.domain.trip_schemas import (
    RouteStopType,
    TimelineDTO,
    TimelineStopDTO,
)


@dataclass(frozen=True)
class _ParsedTimelineStop:
    """
    TimelineStopDTO의 문자열 시각을 datetime으로 변환해 보관하는 내부 모델.

    외부로 반환하는 도메인 모델이 아니므로 파일 내부에서만 사용한다.
    원본 Stop 정보와 파싱된 시각을 함께 보관해 반복 파싱을 방지한다.
    """

    source: TimelineStopDTO
    arrival_at: datetime
    departure_at: datetime


class RoutePlannerTimelineAdapter:
    """
    Route Planner Timeline을 빈 시간 추천 도메인 입력으로 변환한다.

    현재 Route Planner Timeline은 다음처럼 연속된 일정이다.

    계획 시작
    → 출발지
    → 이동
    → POI 체류
    → 이동
    → 다음 POI 체류
    → 이동
    → 도착지
    → 실제 종료

    Stop 사이의 시간은 빈 시간이 아니라 이동 시간이므로,
    planned_start_at부터 actual_end_at까지를 하나의 점유 구간으로 만든다.
    """

    def to_day_availability(
        self,
        timeline: TimelineDTO,
    ) -> DayAvailability:
        """
        TimelineDTO를 DayAvailability로 변환하는 메인 진입점.

        처리 흐름:
        1. Timeline 요약 시각을 datetime으로 파싱
        2. 계획 시작·종료·실제 종료 시각 검증
        3. Timeline Stop 전체 파싱 및 구조 검증
        4. 총 체류시간과 총 이동시간 검증
        5. 하나의 BusyTimeInterval 생성
        6. DayAvailability 반환
        """

        # ------------------------------------------------------------
        # 1단계: Timeline 상위 필드의 문자열 시각 파싱
        # ------------------------------------------------------------
        planned_start_at = self._parse_datetime(
            value=timeline.planned_start_at,
            field_name="TimelineDTO.planned_start_at",
        )
        planned_end_at = self._parse_datetime(
            value=timeline.planned_end_at,
            field_name="TimelineDTO.planned_end_at",
        )
        actual_end_at = self._parse_datetime(
            value=timeline.actual_end_at,
            field_name="TimelineDTO.actual_end_at",
        )

        # ------------------------------------------------------------
        # 2단계: 계획 시작·종료·실제 종료 시각의 정합성 검증
        # ------------------------------------------------------------
        self._validate_summary_times(
            timeline=timeline,
            planned_start_at=planned_start_at,
            planned_end_at=planned_end_at,
            actual_end_at=actual_end_at,
        )

        # ------------------------------------------------------------
        # 3단계: 각 Timeline Stop의 시각과 구조 검증
        # ------------------------------------------------------------
        parsed_stops = self._parse_and_validate_stops(
            timeline=timeline,
            planned_start_at=planned_start_at,
            actual_end_at=actual_end_at,
        )

        # ------------------------------------------------------------
        # 4단계: Timeline의 합계 정보 검증
        #
        # total_stay_minutes:
        # 모든 Stop의 stay_minutes 합계와 일치해야 한다.
        #
        # total_travel_minutes:
        # 이전 Stop 출발부터 다음 Stop 도착까지의 합계와 일치해야 한다.
        # ------------------------------------------------------------
        self._validate_total_minutes(
            timeline=timeline,
            parsed_stops=parsed_stops,
        )

        # ------------------------------------------------------------
        # 5단계: 빈 시간 추천 도메인의 점유 종료 시각 결정
        #
        # 실제 종료가 계획 종료보다 빠른 경우:
        #   실제 종료까지만 점유한다.
        #
        # 실제 종료가 계획 종료를 초과한 경우:
        #   계획 종료까지 전체가 점유된 것으로 표현한다.
        #
        # DayAvailability의 범위 밖으로 BusyTimeInterval이
        # 나가지 않도록 계획 종료 시각에서 제한한다.
        # ------------------------------------------------------------
        busy_end_at = min(
            actual_end_at,
            planned_end_at,
        )

        # 실제 종료가 계획 시작과 같다면 점유 시간이 0분이다.
        # BusyTimeInterval은 종료가 시작보다 늦어야 하므로
        # 이 경우에는 점유 구간을 만들지 않는다.
        if busy_end_at == planned_start_at:
            busy_intervals: tuple[BusyTimeInterval, ...] = ()
        else:
            # 현재 Route Planner Timeline 전체는 연속된 일정이므로
            # 여러 Stop을 각각 점유 구간으로 나누지 않고
            # 계획 시작부터 실제 종료까지 하나의 구간으로 표현한다.
            busy_intervals = (
                BusyTimeInterval(
                    start_at=planned_start_at,
                    end_at=busy_end_at,

                    # 점유 구간이 시작되는 장소는 첫 START Stop이다.
                    start_boundary=ScheduleBoundary(
                        place_id=parsed_stops[0].source.place_id,
                    ),

                    # 점유 구간이 종료되는 장소는 마지막 END Stop이다.
                    end_boundary=ScheduleBoundary(
                        place_id=parsed_stops[-1].source.place_id,
                    ),
                ),
            )

        # ------------------------------------------------------------
        # 6단계: 빈 시간 탐지기가 사용할 도메인 입력 반환
        # ------------------------------------------------------------
        return DayAvailability(
            day_index=timeline.day_index,
            start_at=planned_start_at,
            end_at=planned_end_at,
            busy_intervals=busy_intervals,
        )

    def to_recommendation_time_window(
        self,
        timeline: TimelineDTO,
    ) -> RecommendationTimeWindow:
        """마지막 방문지와 최종 도착지 사이의 추천 삽입 범위를 만든다."""

        # 기존 변환 경로와 같은 Timeline 정합성 검증
        self.to_day_availability(timeline)

        planned_end_at = self._parse_datetime(
            value=timeline.planned_end_at,
            field_name="TimelineDTO.planned_end_at",
        )
        previous_stop = timeline.timeline_stops[-2]
        next_stop = timeline.timeline_stops[-1]
        window_start_at = self._parse_datetime(
            value=previous_stop.departure_at,
            field_name=(
                "TimelineDTO.timeline_stops[-2].departure_at"
            ),
        )

        if window_start_at >= planned_end_at:
            raise RoutePlannerTimelineAdapterError(
                "마지막 방문지 출발 시각은 계획 종료 시각보다 "
                "빨라야 합니다."
            )

        available_minutes = int(
            (planned_end_at - window_start_at).total_seconds()
            // 60
        )

        return RecommendationTimeWindow(
            day_index=timeline.day_index,
            start_at=window_start_at,
            end_at=planned_end_at,
            available_minutes=available_minutes,
            previous_place_id=previous_stop.place_id,
            next_place_id=next_stop.place_id,
        )

    def to_route_leg_insertion_windows(
        self,
        timeline: TimelineDTO,
    ) -> tuple[RouteLegInsertionWindow, ...]:
        """Timeline의 모든 이동 구간을 추천 삽입 범위로 변환한다."""

        # 기존 변환과 동일한 Timeline 계약 검증
        self.to_day_availability(timeline)

        original_timeline_end_at = self._parse_datetime(
            value=timeline.actual_end_at,
            field_name="TimelineDTO.actual_end_at",
        )
        planned_end_at = self._parse_datetime(
            value=timeline.planned_end_at,
            field_name="TimelineDTO.planned_end_at",
        )
        parsed_stops = tuple(
            self._parse_stop(stop=stop, index=index)
            for index, stop in enumerate(timeline.timeline_stops)
        )

        windows: list[RouteLegInsertionWindow] = []
        for leg_index, (previous_stop, next_stop) in enumerate(
            zip(parsed_stops, parsed_stops[1:])
        ):
            original_travel_minutes = int(
                (
                    next_stop.arrival_at
                    - previous_stop.departure_at
                ).total_seconds()
                // 60
            )
            windows.append(
                RouteLegInsertionWindow(
                    day_index=timeline.day_index,
                    leg_index=leg_index,
                    previous_place_id=(
                        previous_stop.source.place_id
                    ),
                    next_place_id=next_stop.source.place_id,
                    previous_departure_at=(
                        previous_stop.departure_at
                    ),
                    next_arrival_at=next_stop.arrival_at,
                    original_travel_minutes=(
                        original_travel_minutes
                    ),
                    original_timeline_end_at=(
                        original_timeline_end_at
                    ),
                    planned_end_at=planned_end_at,
                )
            )

        return tuple(windows)

    def to_timezone_aware_route_leg_insertion_windows(
        self,
        timeline: TimelineDTO,
        timezone: ZoneInfo,
    ) -> tuple[RouteLegInsertionWindow, ...]:
        """모든 삽입 구간 시각을 명시적인 여행 시간대로 변환한다."""

        if not isinstance(timezone, ZoneInfo):
            raise TypeError("timezone은 ZoneInfo여야 합니다.")

        windows = self.to_route_leg_insertion_windows(timeline)
        return tuple(
            replace(
                window,
                previous_departure_at=self._apply_timezone(
                    window.previous_departure_at,
                    timezone,
                ),
                next_arrival_at=self._apply_timezone(
                    window.next_arrival_at,
                    timezone,
                ),
                original_timeline_end_at=self._apply_timezone(
                    window.original_timeline_end_at,
                    timezone,
                ),
                planned_end_at=self._apply_timezone(
                    window.planned_end_at,
                    timezone,
                ),
            )
            for window in windows
        )

    @staticmethod
    def _apply_timezone(value: datetime, timezone: ZoneInfo) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone)
        return value.astimezone(timezone)

    def _validate_summary_times(
        self,
        timeline: TimelineDTO,
        planned_start_at: datetime,
        planned_end_at: datetime,
        actual_end_at: datetime,
    ) -> None:
        """
        Timeline 상위 수준의 시각 필드를 검증한다.

        검증 항목:
        - 세 시각의 시간대 형식이 동일한지
        - 계획 종료가 계획 시작보다 늦은지
        - 실제 종료가 계획 시작보다 빠르지 않은지
        - exceeds_planned_end 값이 실제 시각 관계와 일치하는지
        """

        # aware datetime과 naive datetime이 섞이면
        # 비교 및 시간 계산 결과를 신뢰할 수 없으므로 실패시킨다.
        self._validate_matching_timezone_awareness(
            values=(
                planned_start_at,
                planned_end_at,
                actual_end_at,
            )
        )

        if planned_end_at <= planned_start_at:
            raise RoutePlannerTimelineAdapterError(
                "계획 종료 시각은 계획 시작 시각보다 늦어야 합니다."
            )

        # 실제 종료와 계획 시작이 같은 것은 허용한다.
        # 예: 방문 장소 없이 출발과 종료가 같은 시각인 일정
        if actual_end_at < planned_start_at:
            raise RoutePlannerTimelineAdapterError(
                "실제 종료 시각은 계획 시작 시각보다 빠를 수 없습니다."
            )

        # 실제 시각을 기준으로 초과 여부를 다시 계산한다.
        expected_exceeds_planned_end = (
            actual_end_at > planned_end_at
        )

        # DTO에 저장된 Boolean 값이 실제 시각 관계와 다르면
        # Timeline 자체의 정합성이 깨진 것으로 판단한다.
        if (
            timeline.exceeds_planned_end
            != expected_exceeds_planned_end
        ):
            raise RoutePlannerTimelineAdapterError(
                "TimelineDTO.exceeds_planned_end 값이 "
                "실제 종료 시각과 일치하지 않습니다."
            )

    def _parse_and_validate_stops(
        self,
        timeline: TimelineDTO,
        planned_start_at: datetime,
        actual_end_at: datetime,
    ) -> list[_ParsedTimelineStop]:
        """
        Timeline Stop 전체를 파싱하고 구조를 검증한다.

        검증 흐름:
        1. Stop 목록이 비어 있지 않은지 확인
        2. 모든 도착·출발 시각 파싱
        3. Timeline 전체의 시간대 형식 확인
        4. START → POI → END 타입 구조 확인
        5. 첫 Stop과 마지막 Stop의 경계 시각 확인
        6. Stop 사이의 시간 순서 확인
        """

        if not timeline.timeline_stops:
            raise RoutePlannerTimelineAdapterError(
                "TimelineDTO.timeline_stops는 비어 있을 수 없습니다."
            )

        # 각 Stop의 문자열 시각을 datetime으로 변환한다.
        parsed_stops = [
            self._parse_stop(
                stop=stop,
                index=index,
            )
            for index, stop in enumerate(
                timeline.timeline_stops
            )
        ]

        # Stop 시각과 Timeline 상위 시각의 시간대 형식이
        # 전부 동일한지 확인한다.
        stop_datetime_values = tuple(
            value
            for parsed_stop in parsed_stops
            for value in (
                parsed_stop.arrival_at,
                parsed_stop.departure_at,
            )
        )

        self._validate_matching_timezone_awareness(
            values=(
                *stop_datetime_values,
                planned_start_at,
                actual_end_at,
            )
        )

        # Stop 타입은 START → POI 여러 개 → END 구조여야 한다.
        self._validate_stop_types(
            parsed_stops
        )

        # 첫 START와 마지막 END 시각이
        # Timeline의 계획 시작 및 실제 종료와 일치해야 한다.
        self._validate_stop_boundaries(
            parsed_stops=parsed_stops,
            planned_start_at=planned_start_at,
            actual_end_at=actual_end_at,
        )

        # 뒤 Stop이 앞 Stop보다 먼저 시작하는 경우를 차단한다.
        self._validate_stop_order(
            parsed_stops
        )

        return parsed_stops

    def _parse_stop(
        self,
        stop: TimelineStopDTO,
        index: int,
    ) -> _ParsedTimelineStop:
        """
        TimelineStopDTO 하나를 파싱하고 Stop 내부 값을 검증한다.

        검증 항목:
        - arrival_at과 departure_at이 올바른 ISO 8601인지
        - 출발 시각이 도착 시각보다 빠르지 않은지
        - stay_minutes가 실제 체류 시간과 일치하는지
        """

        arrival_at = self._parse_datetime(
            value=stop.arrival_at,
            field_name=(
                f"TimelineDTO.timeline_stops[{index}].arrival_at"
            ),
        )
        departure_at = self._parse_datetime(
            value=stop.departure_at,
            field_name=(
                f"TimelineDTO.timeline_stops[{index}].departure_at"
            ),
        )

        # arrival_at과 departure_at을 직접 비교하기 전에
        # 두 값의 시간대 인식 여부가 동일한지 먼저 확인한다.
        #
        # naive datetime과 timezone-aware datetime을 바로 비교하면
        # Python의 TypeError가 발생하므로, 도메인 예외로 변환하기 위한
        # 선행 검증이 필요하다.
        self._validate_matching_timezone_awareness(
            values=(
                arrival_at,
                departure_at,
            )
        )

        if departure_at < arrival_at:
            raise RoutePlannerTimelineAdapterError(
                f"Timeline Stop {index}의 출발 시각은 "
                "도착 시각보다 빠를 수 없습니다."
            )

        # 실제 도착·출발 시각 차이로 체류시간을 계산한다.
        actual_stay_minutes = self._duration_minutes(
            start_at=arrival_at,
            end_at=departure_at,
        )

        # DTO의 stay_minutes와 실제 시각 차이가 다르면
        # Timeline의 체류시간 정보가 일관되지 않은 상태다.
        if actual_stay_minutes != stop.stay_minutes:
            raise RoutePlannerTimelineAdapterError(
                f"Timeline Stop {index}의 stay_minutes가 "
                "실제 체류 시간과 일치하지 않습니다."
            )

        return _ParsedTimelineStop(
            source=stop,
            arrival_at=arrival_at,
            departure_at=departure_at,
        )

    def _validate_stop_types(
        self,
        parsed_stops: list[_ParsedTimelineStop],
    ) -> None:
        """
        Timeline Stop 타입의 순서를 검증한다.

        허용 구조:
        - 첫 번째 Stop: START
        - 중간 Stop: POI
        - 마지막 Stop: END
        """

        first_stop = parsed_stops[0]
        last_stop = parsed_stops[-1]

        if (
            first_stop.source.stop_type
            != RouteStopType.START
        ):
            raise RoutePlannerTimelineAdapterError(
                "첫 Timeline Stop의 stop_type은 START여야 합니다."
            )

        if (
            last_stop.source.stop_type
            != RouteStopType.END
        ):
            raise RoutePlannerTimelineAdapterError(
                "마지막 Timeline Stop의 stop_type은 END여야 합니다."
            )

        # 첫 번째와 마지막을 제외한 모든 Stop은 POI여야 한다.
        for index, parsed_stop in enumerate(
            parsed_stops[1:-1],
            start=1,
        ):
            if (
                parsed_stop.source.stop_type
                != RouteStopType.POI
            ):
                raise RoutePlannerTimelineAdapterError(
                    f"중간 Timeline Stop {index}의 "
                    "stop_type은 POI여야 합니다."
                )

    def _validate_stop_boundaries(
        self,
        parsed_stops: list[_ParsedTimelineStop],
        planned_start_at: datetime,
        actual_end_at: datetime,
    ) -> None:
        """
        Timeline의 첫 Stop과 마지막 Stop 시각을 검증한다.

        Route Planner의 현재 계약:
        - START Stop의 도착·출발 시각 = planned_start_at
        - END Stop의 도착·출발 시각 = actual_end_at
        """

        first_stop = parsed_stops[0]
        last_stop = parsed_stops[-1]

        if (
            first_stop.arrival_at != planned_start_at
            or first_stop.departure_at != planned_start_at
        ):
            raise RoutePlannerTimelineAdapterError(
                "첫 Timeline Stop의 도착·출발 시각은 "
                "계획 시작 시각과 일치해야 합니다."
            )

        if (
            last_stop.arrival_at != actual_end_at
            or last_stop.departure_at != actual_end_at
        ):
            raise RoutePlannerTimelineAdapterError(
                "마지막 Timeline Stop의 도착·출발 시각은 "
                "실제 종료 시각과 일치해야 합니다."
            )

    def _validate_stop_order(
        self,
        parsed_stops: list[_ParsedTimelineStop],
    ) -> None:
        """
        Timeline Stop이 시간순으로 배치되어 있는지 검증한다.

        정상 관계:
        이전 Stop departure_at <= 다음 Stop arrival_at

        두 Stop 사이의 차이는 이동시간으로 해석한다.
        """

        for current_index, (
            previous_stop,
            current_stop,
        ) in enumerate(
            zip(
                parsed_stops,
                parsed_stops[1:],
            ),
            start=1,
        ):
            if (
                current_stop.arrival_at
                < previous_stop.departure_at
            ):
                raise RoutePlannerTimelineAdapterError(
                    f"Timeline Stop {current_index - 1}과 "
                    f"{current_index}의 시간 순서가 겹칠 수 없습니다."
                )

    def _validate_total_minutes(
        self,
        timeline: TimelineDTO,
        parsed_stops: list[_ParsedTimelineStop],
    ) -> None:
        """
        TimelineDTO의 총 체류시간과 총 이동시간을 검증한다.

        체류시간:
        각 Stop의 stay_minutes 합계

        이동시간:
        이전 Stop 출발 시각부터 다음 Stop 도착 시각까지의 합계
        """

        # START와 END의 stay_minutes는 보통 0이고,
        # POI의 stay_minutes가 실제 체류시간에 포함된다.
        calculated_stay_minutes = sum(
            parsed_stop.source.stay_minutes
            for parsed_stop in parsed_stops
        )

        if (
            calculated_stay_minutes
            != timeline.total_stay_minutes
        ):
            raise RoutePlannerTimelineAdapterError(
                "TimelineDTO.total_stay_minutes가 "
                "정류장별 체류 시간 합계와 일치하지 않습니다."
            )

        # Stop 사이의 시간 차이는 이동시간이다.
        calculated_travel_minutes = sum(
            self._duration_minutes(
                start_at=previous_stop.departure_at,
                end_at=current_stop.arrival_at,
            )
            for previous_stop, current_stop in zip(
                parsed_stops,
                parsed_stops[1:],
            )
        )

        if (
            calculated_travel_minutes
            != timeline.total_travel_minutes
        ):
            raise RoutePlannerTimelineAdapterError(
                "TimelineDTO.total_travel_minutes가 "
                "정류장 사이 이동 시간 합계와 일치하지 않습니다."
            )

    def _parse_datetime(
        self,
        value: str,
        field_name: str,
    ) -> datetime:
        """
        ISO 8601 문자열을 datetime으로 변환한다.

        예:
        - 2026-08-01T10:00
        - 2026-08-01T10:00+09:00

        초와 마이크로초가 포함된 시각은 허용하지 않는다.
        현재 추천 도메인이 분 단위로 동작하기 때문이다.
        """

        try:
            parsed = datetime.fromisoformat(
                value
            )
        except ValueError as exc:
            raise RoutePlannerTimelineAdapterError(
                f"{field_name}은 올바른 ISO 8601 형식이어야 합니다."
            ) from exc

        if (
            parsed.second != 0
            or parsed.microsecond != 0
        ):
            raise RoutePlannerTimelineAdapterError(
                f"{field_name}은 분 단위로 입력해야 합니다."
            )

        return parsed

    def _duration_minutes(
        self,
        start_at: datetime,
        end_at: datetime,
    ) -> int:
        """
        두 datetime 사이의 간격을 정수 분으로 계산한다.

        초 단위 나머지가 있으면 임의로 버리지 않고 실패시킨다.
        예를 들어 30분 30초를 30분으로 축소하지 않는다.
        """

        total_seconds = int(
            (end_at - start_at).total_seconds()
        )
        minutes, remaining_seconds = divmod(
            total_seconds,
            60,
        )

        if remaining_seconds != 0:
            raise RoutePlannerTimelineAdapterError(
                "Timeline 시간 간격은 분 단위로 표현되어야 합니다."
            )

        return minutes

    def _validate_matching_timezone_awareness(
        self,
        values: tuple[datetime, ...],
    ) -> None:
        """
        전달받은 모든 datetime의 시간대 인식 여부가 같은지 검증한다.

        허용:
        - 모두 naive datetime
        - 모두 timezone-aware datetime

        거부:
        - naive datetime과 timezone-aware datetime 혼합
        """

        if not values:
            return

        # 첫 번째 시각의 형식을 기준으로 삼는다.
        expected_is_aware = self._is_timezone_aware(
            values[0]
        )

        for value in values[1:]:
            current_is_aware = self._is_timezone_aware(
                value
            )

            if current_is_aware != expected_is_aware:
                raise RoutePlannerTimelineAdapterError(
                    "Timeline의 모든 시각은 동일한 "
                    "시간대 형식을 사용해야 합니다."
                )

    def _is_timezone_aware(
        self,
        value: datetime,
    ) -> bool:
        """
        datetime이 명시적인 UTC offset을 가진 값인지 확인한다.

        예:
        - 2026-08-01T10:00       → False
        - 2026-08-01T10:00+09:00 → True
        """

        return (
            value.tzinfo is not None
            and value.utcoffset() is not None
        )
