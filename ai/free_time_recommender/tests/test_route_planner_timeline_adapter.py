# Route Planner Timeline 어댑터 단위 테스트
import pytest

from ai.free_time_recommender.adapters.errors import (
    RoutePlannerTimelineAdapterError,
)
from ai.free_time_recommender.adapters.route_planner_timeline_adapter import (
    RoutePlannerTimelineAdapter,
)
from ai.free_time_recommender.application.detect_free_time_slots import (
    DetectFreeTimeSlots,
)
from ai.route_planner.domain.schemas import TravelMode
from ai.route_planner.domain.trip_schemas import (
    RouteStopType,
    TimelineDTO,
    TimelineStopDTO,
)

# 테스트 도우미 함수: TimelineStopDTO 생성
def make_stop(
    stop_type: RouteStopType,
    place_id: str,
    name: str,
    arrival_at: str,
    departure_at: str,
    stay_minutes: int,
) -> TimelineStopDTO:
    return TimelineStopDTO(
        stop_type=stop_type,
        place_id=place_id,
        name=name,
        arrival_at=arrival_at,
        departure_at=departure_at,
        stay_minutes=stay_minutes,
    )


# 여러 POI가 포함된 정상 Timeline을 생성하는 테스트 도우미
def make_timeline() -> TimelineDTO:
    return TimelineDTO(
        day_index=1,
        travel_mode=TravelMode.DRIVE,
        planned_start_at="2026-08-01T10:00",
        planned_end_at="2026-08-01T20:00",
        actual_end_at="2026-08-01T15:00",
        total_travel_minutes=90,
        total_stay_minutes=210,
        timeline_stops=[
            make_stop(
                RouteStopType.START,
                "start",
                "출발지",
                "2026-08-01T10:00",
                "2026-08-01T10:00",
                0,
            ),
            make_stop(
                RouteStopType.POI,
                "poi-a",
                "관광지 A",
                "2026-08-01T10:20",
                "2026-08-01T11:20",
                60,
            ),
            make_stop(
                RouteStopType.POI,
                "poi-b",
                "식당 B",
                "2026-08-01T11:50",
                "2026-08-01T13:20",
                90,
            ),
            make_stop(
                RouteStopType.POI,
                "poi-c",
                "관광지 C",
                "2026-08-01T13:35",
                "2026-08-01T14:35",
                60,
            ),
            make_stop(
                RouteStopType.END,
                "end",
                "도착지",
                "2026-08-01T15:00",
                "2026-08-01T15:00",
                0,
            ),
        ],
        exceeds_planned_end=False,
        warnings=[],
    )


def replace_stop(
    timeline: TimelineDTO,
    index: int,
    **updates,
) -> TimelineDTO:
    stops = list(timeline.timeline_stops)
    stops[index] = stops[index].model_copy(
        update=updates,
    )

    return timeline.model_copy(
        update={
            "timeline_stops": stops,
        }
    )


# 여러 POI Timeline을 하나의 연속된 점유 구간으로 변환하는지 검증
def test_to_day_availability_converts_multiple_poi_timeline():
    availability = (
        RoutePlannerTimelineAdapter()
        .to_day_availability(
            make_timeline()
        )
    )

    assert availability.day_index == 1
    assert availability.start_at.isoformat() == (
        "2026-08-01T10:00:00"
    )
    assert availability.end_at.isoformat() == (
        "2026-08-01T20:00:00"
    )
    assert len(availability.busy_intervals) == 1

    busy_interval = availability.busy_intervals[0]

    assert busy_interval.start_at.isoformat() == (
        "2026-08-01T10:00:00"
    )
    assert busy_interval.end_at.isoformat() == (
        "2026-08-01T15:00:00"
    )
    assert busy_interval.start_boundary is not None
    assert busy_interval.end_boundary is not None
    assert busy_interval.start_boundary.place_id == "start"
    assert busy_interval.end_boundary.place_id == "end"


# 변환 결과로 실제 종료 이후의 빈 시간대를 탐지하는지 검증
def test_adapter_output_detects_remaining_free_time():
    availability = (
        RoutePlannerTimelineAdapter()
        .to_day_availability(
            make_timeline()
        )
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=60,
    )

    assert len(slots) == 1

    slot = slots[0]

    assert slot.start_at.isoformat() == (
        "2026-08-01T15:00:00"
    )
    assert slot.end_at.isoformat() == (
        "2026-08-01T20:00:00"
    )
    assert slot.available_minutes == 300
    assert slot.previous_place_id == "end"
    assert slot.next_place_id is None


# 마지막 방문지와 등록된 도착지 사이의 추천 삽입 범위 변환 검증
def test_adapter_builds_recommendation_window_before_end_place():
    window = (
        RoutePlannerTimelineAdapter()
        .to_recommendation_time_window(make_timeline())
    )

    assert window.day_index == 1
    assert window.start_at.isoformat() == "2026-08-01T14:35:00"
    assert window.end_at.isoformat() == "2026-08-01T20:00:00"
    assert window.available_minutes == 325
    assert window.previous_place_id == "poi-c"
    assert window.next_place_id == "end"


# 방문 POI가 없으면 출발지와 도착지 사이의 추천 삽입 범위 변환 검증
def test_adapter_builds_recommendation_window_between_start_and_end():
    timeline = make_timeline().model_copy(
        update={
            "actual_end_at": "2026-08-01T10:30",
            "total_travel_minutes": 30,
            "total_stay_minutes": 0,
            "timeline_stops": [
                make_stop(
                    RouteStopType.START,
                    "start",
                    "출발지",
                    "2026-08-01T10:00",
                    "2026-08-01T10:00",
                    0,
                ),
                make_stop(
                    RouteStopType.END,
                    "end",
                    "도착지",
                    "2026-08-01T10:30",
                    "2026-08-01T10:30",
                    0,
                ),
            ],
        }
    )

    window = (
        RoutePlannerTimelineAdapter()
        .to_recommendation_time_window(timeline)
    )

    assert window.start_at.isoformat() == "2026-08-01T10:00:00"
    assert window.available_minutes == 600
    assert window.previous_place_id == "start"
    assert window.next_place_id == "end"


# 마지막 방문지 출발이 계획 종료보다 늦으면 추천 범위 생성 실패 검증
def test_adapter_rejects_window_without_positive_time_budget():
    timeline = make_timeline().model_copy(
        update={
            "planned_end_at": "2026-08-01T14:30",
            "exceeds_planned_end": True,
        }
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="마지막 방문지 출발 시각",
    ):
        (
            RoutePlannerTimelineAdapter()
            .to_recommendation_time_window(timeline)
        )


# Timeline의 모든 연속 Stop을 이동 구간 삽입 범위로 변환 검증
def test_adapter_builds_insertion_window_for_each_route_leg():
    windows = (
        RoutePlannerTimelineAdapter()
        .to_route_leg_insertion_windows(make_timeline())
    )

    assert len(windows) == 4
    assert [
        (
            window.leg_index,
            window.previous_place_id,
            window.next_place_id,
            window.original_travel_minutes,
        )
        for window in windows
    ] == [
        (0, "start", "poi-a", 20),
        (1, "poi-a", "poi-b", 30),
        (2, "poi-b", "poi-c", 15),
        (3, "poi-c", "end", 25),
    ]

    assert windows[1].previous_departure_at.isoformat() == (
        "2026-08-01T11:20:00"
    )
    assert windows[1].next_arrival_at.isoformat() == (
        "2026-08-01T11:50:00"
    )
    assert windows[1].original_timeline_end_at.isoformat() == (
        "2026-08-01T15:00:00"
    )
    assert windows[1].planned_end_at.isoformat() == (
        "2026-08-01T20:00:00"
    )


# 계획 종료를 초과한 Timeline은 계획 범위 전체를 점유하는지 검증
def test_to_day_availability_caps_busy_time_at_planned_end():
    timeline = make_timeline().model_copy(
        update={
            "planned_end_at": "2026-08-01T14:30",
            "exceeds_planned_end": True,
        }
    )

    availability = (
        RoutePlannerTimelineAdapter()
        .to_day_availability(
            timeline
        )
    )

    assert (
        availability.busy_intervals[0]
        .end_at
        .isoformat()
        == "2026-08-01T14:30:00"
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=30,
    )

    assert slots == []


# Timeline Stop이 없으면 변환에 실패하는지 검증
def test_to_day_availability_rejects_empty_stops():
    timeline = make_timeline().model_copy(
        update={
            "timeline_stops": [],
        }
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="timeline_stops는 비어 있을 수 없습니다",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# 올바르지 않은 날짜 문자열이면 변환에 실패하는지 검증
def test_to_day_availability_rejects_invalid_datetime():
    timeline = make_timeline().model_copy(
        update={
            "planned_end_at": "잘못된-시각",
        }
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="ISO 8601",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# 첫 번째 Stop이 START가 아니면 변환에 실패하는지 검증
def test_to_day_availability_rejects_invalid_first_stop_type():
    timeline = replace_stop(
        make_timeline(),
        0,
        stop_type=RouteStopType.POI,
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="stop_type은 START",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# 마지막 Stop이 END가 아니면 변환에 실패하는지 검증
def test_to_day_availability_rejects_invalid_last_stop_type():
    timeline = replace_stop(
        make_timeline(),
        -1,
        stop_type=RouteStopType.POI,
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="stop_type은 END",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# 첫 Stop 시각이 계획 시작과 다르면 변환에 실패하는지 검증
def test_to_day_availability_rejects_first_stop_time_mismatch():
    timeline = replace_stop(
        make_timeline(),
        0,
        arrival_at="2026-08-01T10:01",
        departure_at="2026-08-01T10:01",
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="계획 시작 시각과 일치",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# 마지막 Stop 시각이 실제 종료와 다르면 변환에 실패하는지 검증
def test_to_day_availability_rejects_last_stop_time_mismatch():
    timeline = replace_stop(
        make_timeline(),
        -1,
        arrival_at="2026-08-01T14:59",
        departure_at="2026-08-01T14:59",
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="실제 종료 시각과 일치",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# Stop 사이 시간이 겹치면 변환에 실패하는지 검증
def test_to_day_availability_rejects_overlapping_stops():
    timeline = replace_stop(
        make_timeline(),
        2,
        arrival_at="2026-08-01T11:00",
        departure_at="2026-08-01T12:30",
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="시간 순서가 겹칠 수 없습니다",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# POI의 stay_minutes가 실제 체류 시간과 다르면 실패하는지 검증
def test_to_day_availability_rejects_stop_stay_minutes_mismatch():
    timeline = replace_stop(
        make_timeline(),
        1,
        stay_minutes=59,
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="실제 체류 시간과 일치하지 않습니다",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# 전체 체류 시간 합계가 정류장별 체류 시간과 다르면 실패하는지 검증
def test_to_day_availability_rejects_total_stay_minutes_mismatch():
    timeline = make_timeline().model_copy(
        update={
            "total_stay_minutes": 209,
        }
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="체류 시간 합계와 일치하지 않습니다",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# 전체 이동 시간 합계가 Stop 사이 이동 시간과 다르면 실패하는지 검증
def test_to_day_availability_rejects_total_travel_minutes_mismatch():
    timeline = make_timeline().model_copy(
        update={
            "total_travel_minutes": 89,
        }
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="이동 시간 합계와 일치하지 않습니다",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# 초과 여부가 실제 종료 시각과 일치하지 않으면 실패하는지 검증
def test_to_day_availability_rejects_invalid_exceeds_flag():
    timeline = make_timeline().model_copy(
        update={
            "exceeds_planned_end": True,
        }
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="exceeds_planned_end 값이",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )


# Timeline 시각의 시간대 형식이 섞여 있으면 실패하는지 검증
def test_to_day_availability_rejects_mixed_timezone_awareness():
    timeline = replace_stop(
        make_timeline(),
        1,
        arrival_at="2026-08-01T10:20+09:00",
    )

    with pytest.raises(
        RoutePlannerTimelineAdapterError,
        match="동일한 시간대 형식",
    ):
        RoutePlannerTimelineAdapter().to_day_availability(
            timeline
        )
