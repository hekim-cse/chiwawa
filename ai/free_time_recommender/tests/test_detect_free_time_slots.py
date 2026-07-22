# 빈 시간대 탐지 유스케이스 단위 테스트
from datetime import datetime

import pytest

from ai.free_time_recommender.application.detect_free_time_slots import (
    DetectFreeTimeSlots,
)
from ai.free_time_recommender.domain.errors import (
    InvalidAvailabilityError,
    InvalidBusyIntervalError,
    OverlappingBusyIntervalsError,
)
from ai.free_time_recommender.domain.models import (
    BusyTimeInterval,
    DayAvailability,
    ScheduleBoundary,
)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(
        year=2026,
        month=8,
        day=1,
        hour=hour,
        minute=minute,
    )


def busy(
    start_hour: int,
    end_hour: int,
    start_place_id: str,
    end_place_id: str,
) -> BusyTimeInterval:
    return BusyTimeInterval(
        start_at=at(start_hour),
        end_at=at(end_hour),
        start_boundary=ScheduleBoundary(
            place_id=start_place_id,
        ),
        end_boundary=ScheduleBoundary(
            place_id=end_place_id,
        ),
    )


# 점유 구간 사이와 일정 종료 후 빈 시간을 모두 반환하는지 검증
def test_execute_detects_slots_between_busy_intervals():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(20),
        busy_intervals=(
            busy(10, 12, "start", "poi-a"),
            busy(15, 17, "poi-b", "poi-c"),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=60,
    )

    assert len(slots) == 2

    assert slots[0].start_at == at(12)
    assert slots[0].end_at == at(15)
    assert slots[0].available_minutes == 180
    assert slots[0].previous_place_id == "poi-a"
    assert slots[0].next_place_id == "poi-b"

    assert slots[1].start_at == at(17)
    assert slots[1].end_at == at(20)
    assert slots[1].available_minutes == 180
    assert slots[1].previous_place_id == "poi-c"
    assert slots[1].next_place_id is None


# 점유 구간이 입력 순서와 관계없이 시간순으로 처리되는지 검증
def test_execute_sorts_busy_intervals_before_detection():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(20),
        busy_intervals=(
            busy(15, 17, "poi-b", "poi-c"),
            busy(10, 12, "start", "poi-a"),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=60,
    )

    assert [
        (slot.start_at, slot.end_at)
        for slot in slots
    ] == [
        (at(12), at(15)),
        (at(17), at(20)),
    ]


# 점유 구간이 없으면 하루 전체를 빈 시간대로 반환하는지 검증
def test_execute_returns_full_day_when_no_busy_intervals_exist():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(20),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=60,
    )

    assert len(slots) == 1
    assert slots[0].start_at == at(10)
    assert slots[0].end_at == at(20)
    assert slots[0].available_minutes == 600
    assert slots[0].previous_place_id is None
    assert slots[0].next_place_id is None


# 일정 시작 전 빈 시간대의 다음 장소 경계를 반환하는지 검증
def test_execute_detects_slot_before_first_busy_interval():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(20),
        busy_intervals=(
            busy(12, 20, "poi-a", "end"),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=60,
    )

    assert len(slots) == 1
    assert slots[0].start_at == at(10)
    assert slots[0].end_at == at(12)
    assert slots[0].previous_place_id is None
    assert slots[0].next_place_id == "poi-a"


# 최소 추천 시간과 정확히 같은 슬롯을 포함하는지 검증
def test_execute_includes_slot_equal_to_minimum_minutes():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(13),
        busy_intervals=(
            busy(10, 12, "start", "poi-a"),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=60,
    )

    assert len(slots) == 1
    assert slots[0].available_minutes == 60


# 최소 추천 시간보다 짧은 슬롯은 제외하는지 검증
def test_execute_excludes_slot_shorter_than_minimum_minutes():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(12, 59),
        busy_intervals=(
            busy(10, 12, "start", "poi-a"),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=60,
    )

    assert slots == []


# 서로 인접한 점유 구간은 겹침으로 판단하지 않는지 검증
def test_execute_allows_adjacent_busy_intervals():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(20),
        busy_intervals=(
            busy(10, 12, "start", "poi-a"),
            busy(12, 15, "poi-a", "poi-b"),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=60,
    )

    assert len(slots) == 1
    assert slots[0].start_at == at(15)
    assert slots[0].end_at == at(20)


# 서로 겹치는 점유 구간은 자동 병합하지 않고 실패하는지 검증
def test_execute_rejects_overlapping_busy_intervals():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(20),
        busy_intervals=(
            busy(10, 13, "start", "poi-a"),
            busy(12, 15, "poi-b", "poi-c"),
        ),
    )

    with pytest.raises(
        OverlappingBusyIntervalsError,
        match="겹칠 수 없습니다",
    ):
        DetectFreeTimeSlots().execute(
            availability=availability,
            minimum_slot_minutes=60,
        )


# 최소 추천 시간이 0 이하이면 실패하는지 검증
@pytest.mark.parametrize(
    "minimum_slot_minutes",
    [0, -1],
)
def test_execute_rejects_non_positive_minimum_minutes(
    minimum_slot_minutes: int,
):
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(20),
    )

    with pytest.raises(
        ValueError,
        match="minimum_slot_minutes는 1 이상",
    ):
        DetectFreeTimeSlots().execute(
            availability=availability,
            minimum_slot_minutes=minimum_slot_minutes,
        )


# 하루 종료 시각이 시작 시각보다 늦지 않으면 실패하는지 검증
def test_day_availability_rejects_invalid_time_range():
    with pytest.raises(
        InvalidAvailabilityError,
        match="종료 시각은 시작 시각보다 늦어야",
    ):
        DayAvailability(
            day_index=1,
            start_at=at(20),
            end_at=at(10),
        )


# 점유 구간 종료 시각이 시작 시각보다 늦지 않으면 실패하는지 검증
def test_busy_interval_rejects_invalid_time_range():
    with pytest.raises(
        InvalidBusyIntervalError,
        match="종료 시각은 시작 시각보다 늦어야",
    ):
        BusyTimeInterval(
            start_at=at(12),
            end_at=at(12),
        )


# 하루 범위를 벗어난 점유 구간은 실패하는지 검증
def test_day_availability_rejects_out_of_range_busy_interval():
    with pytest.raises(
        InvalidAvailabilityError,
        match="하루 사용 가능 시간 범위 안에",
    ):
        DayAvailability(
            day_index=1,
            start_at=at(10),
            end_at=at(20),
            busy_intervals=(
                busy(9, 12, "start", "poi-a"),
            ),
        )


# 초 단위 시각을 임의로 분 단위 절삭하지 않는지 검증
def test_day_availability_rejects_partial_minute_precision():
    with pytest.raises(
        ValueError,
        match="분 단위로 입력해야",
    ):
        DayAvailability(
            day_index=1,
            start_at=datetime(
                2026,
                8,
                1,
                10,
                0,
                30,
            ),
            end_at=at(20),
        )


# 분 단위 점유 구간을 생성하는 테스트 도우미
def busy_at(
    start_hour: int,
    start_minute: int,
    end_hour: int,
    end_minute: int,
    start_place_id: str | None,
    end_place_id: str | None,
) -> BusyTimeInterval:
    return BusyTimeInterval(
        start_at=at(start_hour, start_minute),
        end_at=at(end_hour, end_minute),
        start_boundary=(
            ScheduleBoundary(place_id=start_place_id)
            if start_place_id is not None
            else None
        ),
        end_boundary=(
            ScheduleBoundary(place_id=end_place_id)
            if end_place_id is not None
            else None
        ),
    )


# 여러 POI 일정 사이에서 최소 시간 이상인 슬롯만 반환하는지 검증
def test_execute_detects_eligible_slots_across_multiple_pois():
    availability = DayAvailability(
        day_index=1,
        start_at=at(9),
        end_at=at(20),
        busy_intervals=(
            busy_at(
                10,
                0,
                11,
                0,
                "start",
                "poi-a",
            ),
            busy_at(
                12,
                0,
                13,
                0,
                "poi-b",
                "poi-c",
            ),
            busy_at(
                14,
                0,
                15,
                0,
                "poi-d",
                "poi-e",
            ),
            busy_at(
                17,
                0,
                18,
                0,
                "poi-f",
                "end",
            ),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=90,
    )

    assert len(slots) == 2

    first_slot = slots[0]

    assert first_slot.start_at == at(15)
    assert first_slot.end_at == at(17)
    assert first_slot.available_minutes == 120
    assert first_slot.previous_place_id == "poi-e"
    assert first_slot.next_place_id == "poi-f"

    second_slot = slots[1]

    assert second_slot.start_at == at(18)
    assert second_slot.end_at == at(20)
    assert second_slot.available_minutes == 120
    assert second_slot.previous_place_id == "end"
    assert second_slot.next_place_id is None


# 여러 POI 사이의 짧은 공백이 최소 추천 시간 미만이면 모두 제외하는지 검증
def test_execute_excludes_multiple_short_slots_between_pois():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(15),
        busy_intervals=(
            busy_at(
                10,
                0,
                11,
                0,
                "start",
                "poi-a",
            ),
            busy_at(
                11,
                30,
                12,
                30,
                "poi-b",
                "poi-c",
            ),
            busy_at(
                13,
                0,
                14,
                0,
                "poi-d",
                "end",
            ),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=61,
    )

    assert slots == []


# 하루 전체가 일정으로 점유되어 있으면 빈 슬롯이 없는지 검증
def test_execute_returns_empty_when_full_day_is_busy():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(20),
        busy_intervals=(
            busy_at(
                10,
                0,
                13,
                0,
                "start",
                "poi-a",
            ),
            busy_at(
                13,
                0,
                17,
                0,
                "poi-a",
                "poi-b",
            ),
            busy_at(
                17,
                0,
                20,
                0,
                "poi-b",
                "end",
            ),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=30,
    )

    assert slots == []


# 장소 경계가 없는 점유 구간도 빈 시간 계산 자체는 가능한지 검증
def test_execute_preserves_missing_place_boundaries_as_none():
    availability = DayAvailability(
        day_index=1,
        start_at=at(10),
        end_at=at(20),
        busy_intervals=(
            busy_at(
                12,
                0,
                15,
                0,
                None,
                None,
            ),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=60,
    )

    assert len(slots) == 2

    assert slots[0].start_at == at(10)
    assert slots[0].end_at == at(12)
    assert slots[0].previous_place_id is None
    assert slots[0].next_place_id is None

    assert slots[1].start_at == at(15)
    assert slots[1].end_at == at(20)
    assert slots[1].previous_place_id is None
    assert slots[1].next_place_id is None


# 서로 다른 일자의 인덱스가 결과 슬롯에 그대로 유지되는지 검증
def test_execute_preserves_day_index():
    availability = DayAvailability(
        day_index=3,
        start_at=at(10),
        end_at=at(20),
        busy_intervals=(
            busy_at(
                10,
                0,
                12,
                0,
                "start-day-3",
                "poi-day-3",
            ),
        ),
    )

    slots = DetectFreeTimeSlots().execute(
        availability=availability,
        minimum_slot_minutes=60,
    )

    assert len(slots) == 1
    assert slots[0].day_index == 3


# 여러 점유 구간 중 뒤쪽 구간이 겹쳐도 명시적으로 실패하는지 검증
def test_execute_rejects_overlap_late_in_multiple_poi_schedule():
    availability = DayAvailability(
        day_index=1,
        start_at=at(9),
        end_at=at(20),
        busy_intervals=(
            busy_at(
                9,
                0,
                10,
                0,
                "start",
                "poi-a",
            ),
            busy_at(
                11,
                0,
                13,
                0,
                "poi-b",
                "poi-c",
            ),
            busy_at(
                12,
                30,
                14,
                0,
                "poi-d",
                "poi-e",
            ),
            busy_at(
                16,
                0,
                18,
                0,
                "poi-f",
                "end",
            ),
        ),
    )

    with pytest.raises(
        OverlappingBusyIntervalsError,
        match="겹칠 수 없습니다",
    ):
        DetectFreeTimeSlots().execute(
            availability=availability,
            minimum_slot_minutes=30,
        )
