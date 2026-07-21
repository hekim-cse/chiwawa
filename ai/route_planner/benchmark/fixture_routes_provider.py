# E2E Benchmark Scenario의 고정 Matrix를 반환하는 Fixture Provider
from __future__ import annotations

from collections.abc import Iterable

from ai.route_planner.benchmark.schemas import (
    BenchmarkMatrixDTO,
)
from ai.route_planner.domain.schemas import (
    Location,
    TravelMode,
    TravelTimeMatrixResult,
)


# 이동 방식과 Location 집합이 정확히 일치하는 Fixture Matrix만 반환
class FixtureTravelTimeMatrixProvider:
    def __init__(
        self,
        matrices: Iterable[BenchmarkMatrixDTO],
    ) -> None:
        self._matrices_by_key: dict[
            tuple[
                TravelMode,
                tuple[str, ...],
            ],
            BenchmarkMatrixDTO,
        ] = {}

        for matrix in matrices:
            key = self._build_key(
                travel_mode=matrix.travel_mode,
                place_ids=(
                    matrix.location_place_ids
                ),
            )

            if key in self._matrices_by_key:
                raise ValueError(
                    "동일한 이동 방식과 "
                    "Location 집합의 Fixture "
                    "Matrix가 중복되었습니다."
                )

            self._matrices_by_key[key] = matrix

    def build_travel_time_matrix_result(
        self,
        locations: list[Location],
        travel_mode: TravelMode,
    ) -> TravelTimeMatrixResult:
        place_ids = [
            location.name
            for location in locations
        ]

        self._validate_unique_place_ids(
            place_ids
        )

        key = self._build_key(
            travel_mode=travel_mode,
            place_ids=place_ids,
        )

        matrix_fixture = (
            self._matrices_by_key.get(key)
        )

        if matrix_fixture is None:
            raise ValueError(
                "요청한 이동 방식과 Location "
                "집합에 대응하는 Fixture Matrix가 "
                "없습니다: "
                f"travel_mode={travel_mode.value}, "
                f"place_ids={sorted(place_ids)}"
            )

        matrix = {
            (
                entry.origin_place_id,
                entry.destination_place_id,
            ): entry.travel_minutes
            for entry in matrix_fixture.entries
        }

        return TravelTimeMatrixResult(
            matrix=matrix,
            missing_elements=[],
        )

    @staticmethod
    def _build_key(
        travel_mode: TravelMode,
        place_ids: Iterable[str],
    ) -> tuple[
        TravelMode,
        tuple[str, ...],
    ]:
        return (
            travel_mode,
            tuple(sorted(place_ids)),
        )

    @staticmethod
    def _validate_unique_place_ids(
        place_ids: list[str],
    ) -> None:
        if (
            len(set(place_ids))
            != len(place_ids)
        ):
            raise ValueError(
                "Fixture Provider 요청의 "
                "Location name은 중복될 수 없습니다."
            )
