# E2E Benchmark 계측 Provider의 호출량과 Matrix 지표 검증
from ai.route_planner.benchmark.instrumented_routes_provider import (
    InstrumentedTravelTimeMatrixProvider,
)
from ai.route_planner.domain.schemas import (
    Location,
    TravelMode,
    TravelTimeElement,
    TravelTimeMatrixResult,
)


# 정상 Matrix와 누락 구간을 함께 반환하는 테스트 Provider
class FakeTravelTimeMatrixProvider:
    def build_travel_time_matrix_result(
        self,
        locations,
        travel_mode,
        departure_time=None,
    ) -> TravelTimeMatrixResult:
        place_ids = [
            location.name
            for location in locations
        ]

        matrix = {
            (origin, destination): 10
            for origin in place_ids
            for destination in place_ids
            if origin != destination
        }

        missing_elements = []

        if travel_mode == TravelMode.TRANSIT:
            missing_elements = [
                TravelTimeElement(
                    origin_name=place_ids[0],
                    destination_name=place_ids[1],
                    origin_index=0,
                    destination_index=1,
                    duration_seconds=None,
                    condition="ROUTE_NOT_FOUND",
                )
            ]

        return TravelTimeMatrixResult(
            matrix=matrix,
            missing_elements=missing_elements,
        )


def make_locations() -> list[Location]:
    return [
        Location(
            name="start",
            lat=35.0,
            lng=139.0,
        ),
        Location(
            name="poi",
            lat=35.1,
            lng=139.1,
        ),
        Location(
            name="end",
            lat=35.2,
            lng=139.2,
        ),
    ]


# 호출 횟수와 이동 방식별 요청 수 집계
def test_snapshot_counts_provider_requests_by_mode():
    provider = (
        InstrumentedTravelTimeMatrixProvider(
            FakeTravelTimeMatrixProvider()
        )
    )

    locations = make_locations()

    provider.build_travel_time_matrix_result(
        locations=locations,
        travel_mode=TravelMode.DRIVE,
    )
    provider.build_travel_time_matrix_result(
        locations=locations,
        travel_mode=TravelMode.TRANSIT,
    )

    snapshot = provider.snapshot()

    assert snapshot.request_count == 2
    assert (
        snapshot.request_count_by_mode[
            TravelMode.DRIVE
        ]
        == 1
    )
    assert (
        snapshot.request_count_by_mode[
            TravelMode.TRANSIT
        ]
        == 1
    )
    assert (
        snapshot.request_count_by_mode[
            TravelMode.WALK
        ]
        == 0
    )


# 요청 Matrix 크기, 반환 구간 및 누락 구간 집계
def test_snapshot_counts_matrix_elements():
    provider = (
        InstrumentedTravelTimeMatrixProvider(
            FakeTravelTimeMatrixProvider()
        )
    )

    provider.build_travel_time_matrix_result(
        locations=make_locations(),
        travel_mode=TravelMode.TRANSIT,
    )

    snapshot = provider.snapshot()

    assert snapshot.expected_element_count == 6
    assert snapshot.returned_element_count == 6
    assert snapshot.missing_element_count == 1
    assert snapshot.total_runtime_ms >= 0

    call = snapshot.calls[0]

    assert call.location_count == 3
    assert call.expected_element_count == 6
    assert call.returned_element_count == 6
    assert call.missing_element_count == 1


# 반복 Benchmark 사이에 이전 계측 결과 초기화
def test_reset_removes_previous_metrics():
    provider = (
        InstrumentedTravelTimeMatrixProvider(
            FakeTravelTimeMatrixProvider()
        )
    )

    provider.build_travel_time_matrix_result(
        locations=make_locations(),
        travel_mode=TravelMode.DRIVE,
    )

    provider.reset()

    snapshot = provider.snapshot()

    assert snapshot.request_count == 0
    assert snapshot.calls == ()
    assert snapshot.expected_element_count == 0
    assert snapshot.returned_element_count == 0
    assert snapshot.missing_element_count == 0
