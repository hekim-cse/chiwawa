# Route Planner E2E Benchmark의 입력 Scenario와 결과 스키마
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from ai.route_planner.domain.schemas import (
    TravelMode,
)
from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)


# Fixture에 저장되는 단일 이동 구간
class BenchmarkTravelTimeEntryDTO(BaseModel):
    origin_place_id: str
    destination_place_id: str
    travel_minutes: int = Field(ge=0)


# 이동 방식과 Location 집합에 대응하는 고정 Matrix
class BenchmarkMatrixDTO(BaseModel):
    travel_mode: TravelMode
    location_place_ids: list[str] = Field(
        min_length=2,
    )
    entries: list[
        BenchmarkTravelTimeEntryDTO
    ]

    @model_validator(mode="after")
    def validate_matrix(
        self,
    ) -> "BenchmarkMatrixDTO":
        if (
            len(set(self.location_place_ids))
            != len(self.location_place_ids)
        ):
            raise ValueError(
                "Benchmark Matrix의 "
                "location_place_ids는 "
                "중복될 수 없습니다."
            )

        location_place_id_set = set(
            self.location_place_ids
        )
        entry_keys: set[
            tuple[str, str]
        ] = set()

        for entry in self.entries:
            key = (
                entry.origin_place_id,
                entry.destination_place_id,
            )

            if key in entry_keys:
                raise ValueError(
                    "Benchmark Matrix에 "
                    "중복 이동 구간이 있습니다: "
                    f"{key}"
                )

            entry_keys.add(key)

            if (
                entry.origin_place_id
                not in location_place_id_set
                or entry.destination_place_id
                not in location_place_id_set
            ):
                raise ValueError(
                    "Benchmark Matrix 이동 구간의 "
                    "place_id가 Location 집합에 "
                    "포함되어야 합니다."
                )

            if (
                entry.origin_place_id
                == entry.destination_place_id
            ):
                raise ValueError(
                    "Benchmark Matrix에 "
                    "자기 자신으로의 이동 구간을 "
                    "정의할 수 없습니다."
                )

        return self


# E2E Benchmark 입력 Scenario
class RoutePlannerE2EBenchmarkScenarioDTO(
    BaseModel
):
    scenario_id: str = Field(min_length=1)
    repeat_count: int = Field(
        default=3,
        ge=1,
        le=10,
    )
    request: TripPlanningRequestDTO
    matrices: list[BenchmarkMatrixDTO] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_matrix_keys(
        self,
    ) -> "RoutePlannerE2EBenchmarkScenarioDTO":
        matrix_keys: set[
            tuple[
                TravelMode,
                tuple[str, ...],
            ]
        ] = set()

        for matrix in self.matrices:
            key = (
                matrix.travel_mode,
                tuple(
                    sorted(
                        matrix.location_place_ids
                    )
                ),
            )

            if key in matrix_keys:
                raise ValueError(
                    "동일한 이동 방식과 "
                    "Location 집합의 Benchmark "
                    "Matrix가 중복되었습니다."
                )

            matrix_keys.add(key)

        return self


# 단일 Benchmark 반복 실행 결과
class RoutePlannerE2EBenchmarkRunDTO(
    BaseModel
):
    runtime_ms: float = Field(ge=0)

    provider_request_count: int = Field(ge=0)
    provider_request_count_by_mode: dict[
        TravelMode,
        int,
    ]
    provider_expected_element_count: int = Field(
        ge=0,
    )
    provider_returned_element_count: int = Field(
        ge=0,
    )
    provider_missing_element_count: int = Field(
        ge=0,
    )
    provider_runtime_ms: float = Field(ge=0)

    assigned_poi_count: int = Field(ge=0)
    unassigned_poi_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    route_option_count: int = Field(ge=0)
    timeline_count: int = Field(ge=0)

    complete_assignment: bool
    result_fingerprint: str


# E2E Benchmark 최종 집계 결과
class RoutePlannerE2EBenchmarkResultDTO(
    BaseModel
):
    scenario_id: str
    repeat_count: int = Field(ge=1)

    total_elapsed_ms: float = Field(ge=0)
    average_runtime_ms: float = Field(ge=0)
    min_runtime_ms: float = Field(ge=0)
    max_runtime_ms: float = Field(ge=0)

    deterministic: bool
    runs: list[
        RoutePlannerE2EBenchmarkRunDTO
    ] = Field(min_length=1)
