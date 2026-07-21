# 하루 사용 가능 범위에서 점유 구간을 제외해 빈 시간대를 계산하는 유스케이스
from datetime import datetime

from ai.free_time_recommender.domain.errors import (
    OverlappingBusyIntervalsError,
)
from ai.free_time_recommender.domain.models import (
    BusyTimeInterval,
    DayAvailability,
    FreeTimeSlot,
)


class DetectFreeTimeSlots:
    """점유 구간 사이의 추천 가능한 빈 시간대를 계산한다."""

    def execute(
        self,
        availability: DayAvailability,
        minimum_slot_minutes: int,
    ) -> list[FreeTimeSlot]:
        if minimum_slot_minutes <= 0:
            raise ValueError(
                "minimum_slot_minutes는 1 이상이어야 합니다."
            )

        ordered_intervals = sorted(
            availability.busy_intervals,
            key=lambda interval: interval.start_at,
        )

        self._validate_non_overlapping_intervals(
            ordered_intervals
        )

        slots: list[FreeTimeSlot] = []
        cursor_at = availability.start_at
        previous_place_id: str | None = None

        for interval in ordered_intervals:
            next_place_id = self._resolve_start_place_id(
                interval
            )

            self._append_slot_when_eligible(
                slots=slots,
                day_index=availability.day_index,
                start_at=cursor_at,
                end_at=interval.start_at,
                minimum_slot_minutes=minimum_slot_minutes,
                previous_place_id=previous_place_id,
                next_place_id=next_place_id,
            )

            cursor_at = interval.end_at
            previous_place_id = self._resolve_end_place_id(
                interval
            )

        self._append_slot_when_eligible(
            slots=slots,
            day_index=availability.day_index,
            start_at=cursor_at,
            end_at=availability.end_at,
            minimum_slot_minutes=minimum_slot_minutes,
            previous_place_id=previous_place_id,
            next_place_id=None,
        )

        return slots

    def _validate_non_overlapping_intervals(
        self,
        intervals: list[BusyTimeInterval],
    ) -> None:
        for previous, current in zip(
            intervals,
            intervals[1:],
        ):
            if current.start_at < previous.end_at:
                raise OverlappingBusyIntervalsError(
                    "점유 시간 구간끼리 겹칠 수 없습니다."
                )

    def _append_slot_when_eligible(
        self,
        slots: list[FreeTimeSlot],
        day_index: int,
        start_at: datetime,
        end_at: datetime,
        minimum_slot_minutes: int,
        previous_place_id: str | None,
        next_place_id: str | None,
    ) -> None:
        if end_at <= start_at:
            return

        available_seconds = int(
            (end_at - start_at).total_seconds()
        )
        available_minutes, remaining_seconds = divmod(
            available_seconds,
            60,
        )

        if remaining_seconds != 0:
            raise ValueError(
                "빈 시간대 길이는 분 단위로 표현되어야 합니다."
            )

        if available_minutes < minimum_slot_minutes:
            return

        slots.append(
            FreeTimeSlot(
                day_index=day_index,
                start_at=start_at,
                end_at=end_at,
                available_minutes=available_minutes,
                previous_place_id=previous_place_id,
                next_place_id=next_place_id,
            )
        )

    def _resolve_start_place_id(
        self,
        interval: BusyTimeInterval,
    ) -> str | None:
        if interval.start_boundary is None:
            return None

        return interval.start_boundary.place_id

    def _resolve_end_place_id(
        self,
        interval: BusyTimeInterval,
    ) -> str | None:
        if interval.end_boundary is None:
            return None

        return interval.end_boundary.place_id
