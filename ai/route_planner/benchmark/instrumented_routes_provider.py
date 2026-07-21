# Route Planner E2E Benchmark에서 Provider 호출량과 실행시간을 계측하는 Decorator
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import List

from ai.route_planner.domain.schemas import (
    Location,
    TravelMode,
    TravelTimeMatrixResult,
)
from ai.route_planner.services.trip_planner_service import (
    TravelTimeMatrixProvider,
)


# 단일 Provider 호출의 계측 결과
@dataclass(frozen=True)
class ProviderCallMetric:
    travel_mode: TravelMode
    location_count: int
    expected_element_count: int
    returned_element_count: int
    missing_element_count: int
    runtime_ms: float


# 전체 Provider 계측 결과
@dataclass(frozen=True)
class ProviderMetricsSnapshot:
    request_count: int
    request_count_by_mode: dict[TravelMode, int]
    expected_element_count: int
    returned_element_count: int
    missing_element_count: int
    total_runtime_ms: float
    calls: tuple[ProviderCallMetric, ...]


# 실제 Provider 호출을 위임하면서 Benchmark 지표를 수집
class InstrumentedTravelTimeMatrixProvider:
    def __init__(
        self,
        delegate: TravelTimeMatrixProvider,
    ) -> None:
        self._delegate = delegate
        self._calls: list[ProviderCallMetric] = []

    def build_travel_time_matrix_result(
        self,
        locations: List[Location],
        travel_mode: TravelMode,
        departure_time: datetime | None = None,
    ) -> TravelTimeMatrixResult:
        started_at = perf_counter()

        result = (
            self._delegate
            .build_travel_time_matrix_result(
                locations=locations,
                travel_mode=travel_mode,
                departure_time=departure_time,
            )
        )

        runtime_ms = (
            perf_counter() - started_at
        ) * 1000

        location_count = len(locations)
        expected_element_count = (
            location_count
            * max(location_count - 1, 0)
        )

        self._calls.append(
            ProviderCallMetric(
                travel_mode=travel_mode,
                location_count=location_count,
                expected_element_count=(
                    expected_element_count
                ),
                returned_element_count=len(
                    result.matrix
                ),
                missing_element_count=len(
                    result.missing_elements
                ),
                runtime_ms=round(
                    runtime_ms,
                    4,
                ),
            )
        )

        return result

    # 현재까지 수집된 값을 불변 Snapshot으로 반환
    def snapshot(
        self,
    ) -> ProviderMetricsSnapshot:
        request_count_by_mode = Counter(
            call.travel_mode
            for call in self._calls
        )

        return ProviderMetricsSnapshot(
            request_count=len(self._calls),
            request_count_by_mode={
                travel_mode: (
                    request_count_by_mode.get(
                        travel_mode,
                        0,
                    )
                )
                for travel_mode in TravelMode
            },
            expected_element_count=sum(
                call.expected_element_count
                for call in self._calls
            ),
            returned_element_count=sum(
                call.returned_element_count
                for call in self._calls
            ),
            missing_element_count=sum(
                call.missing_element_count
                for call in self._calls
            ),
            total_runtime_ms=round(
                sum(
                    call.runtime_ms
                    for call in self._calls
                ),
                4,
            ),
            calls=tuple(self._calls),
        )

    # 반복 Benchmark 실행 사이에 계측값 초기화
    def reset(self) -> None:
        self._calls.clear()
