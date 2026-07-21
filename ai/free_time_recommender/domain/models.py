# 빈 시간대 일정 추천의 순수 도메인 모델
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai.free_time_recommender.domain.errors import (
    InvalidAvailabilityError,
    InvalidBusyIntervalError,
)

# 시간 값 검증 함수
def _validate_minute_precision(
    value: datetime,
    field_name: str,
) -> None:
    """시간 값을 분 단위로만 표현하도록 검증한다."""

    if value.second != 0 or value.microsecond != 0:
        raise ValueError(
            f"{field_name}은 분 단위로 입력해야 합니다."
        )

# 시간대 인식 여부 검증 함수
def _is_timezone_aware(value: datetime) -> bool:
    """datetime 값이 UTC offset을 가진 timezone-aware 값인지 확인한다."""

    return (
        value.tzinfo is not None
        and value.utcoffset() is not None
    )

# 시간대 인식 일치 검증 함수
def _validate_matching_timezone_awareness(
    start_at: datetime,
    end_at: datetime,
    field_name: str,
) -> None:
    """시작과 종료 시각의 시간대 인식 여부가 같은지 검증한다."""

    if _is_timezone_aware(start_at) != _is_timezone_aware(end_at):
        raise ValueError(
            f"{field_name}의 start_at과 end_at은 "
            "동일한 시간대 형식을 사용해야 합니다."
        )


@dataclass(frozen=True)
class ScheduleBoundary:
    """빈 시간대 앞뒤에 위치한 장소 경계."""

    place_id: str

    def __post_init__(self) -> None:
        if not self.place_id.strip():
            raise ValueError(
                "일정 경계의 place_id는 비어 있을 수 없습니다."
            )


@dataclass(frozen=True)
class BusyTimeInterval:
    """하루 일정에서 이미 사용 중인 시간 구간."""

    start_at: datetime
    end_at: datetime
    start_boundary: ScheduleBoundary | None = None
    end_boundary: ScheduleBoundary | None = None

    def __post_init__(self) -> None:
        _validate_minute_precision(
            self.start_at,
            "BusyTimeInterval.start_at",
        )
        _validate_minute_precision(
            self.end_at,
            "BusyTimeInterval.end_at",
        )
        _validate_matching_timezone_awareness(
            self.start_at,
            self.end_at,
            "BusyTimeInterval",
        )

        if self.end_at <= self.start_at:
            raise InvalidBusyIntervalError(
                "점유 구간 종료 시각은 시작 시각보다 늦어야 합니다."
            )


@dataclass(frozen=True)
class DayAvailability:
    """하루의 전체 사용 가능 범위와 점유 구간."""

    day_index: int
    start_at: datetime
    end_at: datetime
    busy_intervals: tuple[BusyTimeInterval, ...] = ()

    def __post_init__(self) -> None:
        if self.day_index < 1:
            raise InvalidAvailabilityError(
                "DayAvailability.day_index는 1 이상이어야 합니다."
            )

        _validate_minute_precision(
            self.start_at,
            "DayAvailability.start_at",
        )
        _validate_minute_precision(
            self.end_at,
            "DayAvailability.end_at",
        )
        _validate_matching_timezone_awareness(
            self.start_at,
            self.end_at,
            "DayAvailability",
        )

        if self.end_at <= self.start_at:
            raise InvalidAvailabilityError(
                "하루 사용 가능 종료 시각은 시작 시각보다 늦어야 합니다."
            )

        availability_is_aware = _is_timezone_aware(self.start_at)

        for interval in self.busy_intervals:
            interval_is_aware = _is_timezone_aware(
                interval.start_at
            )

            if interval_is_aware != availability_is_aware:
                raise InvalidAvailabilityError(
                    "점유 구간과 하루 사용 가능 시간은 "
                    "동일한 시간대 형식을 사용해야 합니다."
                )

            if (
                interval.start_at < self.start_at
                or interval.end_at > self.end_at
            ):
                raise InvalidAvailabilityError(
                    "점유 구간은 하루 사용 가능 시간 범위 안에 "
                    "포함되어야 합니다."
                )


@dataclass(frozen=True)
class FreeTimeSlot:
    """추천 후보를 검토할 수 있는 빈 시간 구간."""

    day_index: int
    start_at: datetime
    end_at: datetime
    available_minutes: int
    previous_place_id: str | None
    next_place_id: str | None

    def __post_init__(self) -> None:
        if self.day_index < 1:
            raise ValueError(
                "FreeTimeSlot.day_index는 1 이상이어야 합니다."
            )

        _validate_minute_precision(
            self.start_at,
            "FreeTimeSlot.start_at",
        )
        _validate_minute_precision(
            self.end_at,
            "FreeTimeSlot.end_at",
        )
        _validate_matching_timezone_awareness(
            self.start_at,
            self.end_at,
            "FreeTimeSlot",
        )

        if self.end_at <= self.start_at:
            raise ValueError(
                "빈 시간대 종료 시각은 시작 시각보다 늦어야 합니다."
            )

        expected_minutes = int(
            (self.end_at - self.start_at).total_seconds()
            // 60
        )

        if self.available_minutes != expected_minutes:
            raise ValueError(
                "FreeTimeSlot.available_minutes는 "
                "실제 빈 시간대 길이와 일치해야 합니다."
            )

        if self.available_minutes <= 0:
            raise ValueError(
                "FreeTimeSlot.available_minutes는 1 이상이어야 합니다."
            )
