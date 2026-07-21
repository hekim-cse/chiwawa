# E2E Benchmark Fixture Provider의 Matrix 선택과 오류 처리 검증
import pytest

from ai.route_planner.benchmark.fixture_routes_provider import (
    FixtureTravelTimeMatrixProvider,
)
from ai.route_planner.benchmark.schemas import (
    BenchmarkMatrixDTO,
)
from ai.route_planner.domain.schemas import (
    Location,
    TravelMode,
)


def make_matrix(
    travel_mode: TravelMode,
) -> BenchmarkMatrixDTO:
    place_ids = [
        "start",
        "poi",
        "end",
    ]

    return BenchmarkMatrixDTO.model_validate(
        {
            "travel_mode": travel_mode,
            "location_place_ids": place_ids,
            "entries": [
                {
                    "origin_place_id": origin,
                    "destination_place_id": (
                        destination
                    ),
                    "travel_minutes": 10,
                }
                for origin in place_ids
                for destination in place_ids
                if origin != destination
            ],
        }
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


# 요청 Location 순서와 관계없이 동일 집합의 Matrix 반환
def test_returns_matrix_for_matching_mode_and_locations():
    provider = FixtureTravelTimeMatrixProvider(
        matrices=[
            make_matrix(
                TravelMode.DRIVE
            ),
        ],
    )

    locations = list(
        reversed(
            make_locations()
        )
    )

    result = (
        provider
        .build_travel_time_matrix_result(
            locations=locations,
            travel_mode=TravelMode.DRIVE,
        )
    )

    assert result.matrix == {
        (
            origin,
            destination,
        ): 10
        for origin in (
            "start",
            "poi",
            "end",
        )
        for destination in (
            "start",
            "poi",
            "end",
        )
        if origin != destination
    }
    assert result.missing_elements == []


# 같은 장소 집합이어도 이동 방식이 다르면 Matrix를 재사용하지 않음
def test_rejects_unknown_travel_mode_matrix():
    provider = FixtureTravelTimeMatrixProvider(
        matrices=[
            make_matrix(
                TravelMode.DRIVE
            ),
        ],
    )

    with pytest.raises(
        ValueError,
        match="Fixture Matrix가 없습니다",
    ):
        (
            provider
            .build_travel_time_matrix_result(
                locations=make_locations(),
                travel_mode=TravelMode.WALK,
            )
        )


# 요청 Location 집합에 정확히 대응하는 Matrix가 없으면 거부
def test_rejects_unknown_location_set():
    provider = FixtureTravelTimeMatrixProvider(
        matrices=[
            make_matrix(
                TravelMode.DRIVE
            ),
        ],
    )

    locations = [
        *make_locations(),
        Location(
            name="extra",
            lat=35.3,
            lng=139.3,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="Fixture Matrix가 없습니다",
    ):
        (
            provider
            .build_travel_time_matrix_result(
                locations=locations,
                travel_mode=TravelMode.DRIVE,
            )
        )


# 요청 Location name 중복 거부
def test_rejects_duplicated_location_names():
    provider = FixtureTravelTimeMatrixProvider(
        matrices=[
            make_matrix(
                TravelMode.DRIVE
            ),
        ],
    )

    locations = [
        Location(
            name="start",
            lat=35.0,
            lng=139.0,
        ),
        Location(
            name="start",
            lat=35.1,
            lng=139.1,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="중복",
    ):
        (
            provider
            .build_travel_time_matrix_result(
                locations=locations,
                travel_mode=TravelMode.DRIVE,
            )
        )
