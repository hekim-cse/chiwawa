# TimelineOptionsBuilder 단위 테스트
import pytest

from ai.route_planner.domain.schemas import TravelMode
from ai.route_planner.domain.trip_schemas import (
    DayConstraintDTO,
    DayPlanDTO,
    PlaceDTO,
    PoiDTO,
    RouteLegDTO,
    RouteOptionDTO,
    RouteStopDTO,
    RouteStopType,
)
from ai.route_planner.solvers.timeline_options_builder import (
    TimelineOptionsBuilder,
)


# 테스트용 출발지 DTO 생성 함수
def make_start_place() -> PlaceDTO:
    return PlaceDTO(
        place_id="start",
        name="오사카 난바역",
        lat=34.6661,
        lng=135.5007,
    )


# 테스트용 도착지 DTO 생성 함수
def make_end_place() -> PlaceDTO:
    return PlaceDTO(
        place_id="end",
        name="우메다역",
        lat=34.7025,
        lng=135.4959,
    )


# 테스트용 POI DTO 생성 함수
def make_poi() -> PoiDTO:
    return PoiDTO(
        poi_id="poi-1",
        place_id="poi-place-1",
        name="도톤보리",
        lat=34.6687,
        lng=135.5013,
        estimated_stay_minutes=60,
    )


# 테스트용 DayConstraintDTO 생성 함수
def make_day_constraint() -> DayConstraintDTO:
    return DayConstraintDTO(
        day_index=1,
        date="2026-08-01",
        start_place=make_start_place(),
        start_time="10:00",
        end_place=make_end_place(),
        end_time="20:00",
        max_place_count=4,
    )


# 테스트용 RouteOptionDTO 생성 함수
def make_route_option(
    travel_mode: TravelMode,
    missing_segments: list[str] | None = None,
    warnings: list[str] | None = None,
) -> RouteOptionDTO:
    return RouteOptionDTO(
        day_index=1,
        travel_mode=travel_mode,
        total_travel_minutes=30,
        ordered_stops=[
            RouteStopDTO(
                stop_type=RouteStopType.START,
                place_id="start",
                name="오사카 난바역",
                lat=34.6661,
                lng=135.5007,
            ),
            RouteStopDTO(
                stop_type=RouteStopType.POI,
                place_id="poi-place-1",
                name="도톤보리",
                lat=34.6687,
                lng=135.5013,
            ),
            RouteStopDTO(
                stop_type=RouteStopType.END,
                place_id="end",
                name="우메다역",
                lat=34.7025,
                lng=135.4959,
            ),
        ],
        route_legs=[
            RouteLegDTO(
                origin_place_id="start",
                destination_place_id="poi-place-1",
                travel_minutes=10,
            ),
            RouteLegDTO(
                origin_place_id="poi-place-1",
                destination_place_id="end",
                travel_minutes=20,
            ),
        ],
        missing_segments=missing_segments or [],
        warnings=warnings or [],
    )


# 테스트용 DayPlanDTO 생성 함수
def make_day_plan() -> DayPlanDTO:
    poi = make_poi()

    return DayPlanDTO(
        day_index=1,
        date="2026-08-01",
        start_place=make_start_place(),
        end_place=make_end_place(),
        assigned_pois=[poi],
        estimated_total_stay_minutes=poi.estimated_stay_minutes,
        assignment_reason="테스트용 장소 배정",
        route_options=[
            make_route_option(
                travel_mode=TravelMode.DRIVE,
            ),
            make_route_option(
                travel_mode=TravelMode.WALK,
            ),
            make_route_option(
                travel_mode=TravelMode.TRANSIT,
                missing_segments=[
                    "start -> poi-place-1",
                ],
                warnings=[
                    "TRANSIT 이동 시간 일부가 누락되었습니다.",
                ],
            ),
        ],
    )


# 완전한 이동 방식에는 Timeline을 생성하는지 검증
def test_assign_timelines_builds_timeline_for_complete_route_options():
    day_plan = make_day_plan()
    builder = TimelineOptionsBuilder()

    updated_day_plan = builder.assign_timelines(
        day_constraint=make_day_constraint(),
        day_plan=day_plan,
    )

    drive_option = updated_day_plan.route_options[0]
    walk_option = updated_day_plan.route_options[1]

    assert drive_option.travel_mode == TravelMode.DRIVE
    assert drive_option.timeline is not None
    assert drive_option.timeline.actual_end_at == "2026-08-01T11:30"

    assert walk_option.travel_mode == TravelMode.WALK
    assert walk_option.timeline is not None
    assert walk_option.timeline.actual_end_at == "2026-08-01T11:30"


# 누락 구간이 있는 이동 방식은 Timeline 없이 유지하는지 검증
def test_assign_timelines_skips_route_option_with_missing_segments():
    day_plan = make_day_plan()
    builder = TimelineOptionsBuilder()

    updated_day_plan = builder.assign_timelines(
        day_constraint=make_day_constraint(),
        day_plan=day_plan,
    )

    transit_option = updated_day_plan.route_options[2]

    assert transit_option.travel_mode == TravelMode.TRANSIT
    assert transit_option.timeline is None
    assert transit_option.missing_segments == [
        "start -> poi-place-1",
    ]
    assert any(
        "시간표를 생성하지 않았습니다" in warning
        for warning in transit_option.warnings
    )


# 누락 구간 경고와 기존 경고가 모두 유지되는지 검증
def test_assign_timelines_preserves_existing_warnings():
    day_plan = make_day_plan()
    builder = TimelineOptionsBuilder()

    updated_day_plan = builder.assign_timelines(
        day_constraint=make_day_constraint(),
        day_plan=day_plan,
    )

    transit_option = updated_day_plan.route_options[2]

    assert "TRANSIT 이동 시간 일부가 누락되었습니다." in (
        transit_option.warnings
    )
    assert len(transit_option.warnings) == 2


# 원본 DayPlanDTO와 RouteOptionDTO를 수정하지 않는지 검증
def test_assign_timelines_does_not_mutate_original_day_plan():
    day_plan = make_day_plan()
    original_route_options = list(day_plan.route_options)
    builder = TimelineOptionsBuilder()

    updated_day_plan = builder.assign_timelines(
        day_constraint=make_day_constraint(),
        day_plan=day_plan,
    )

    assert updated_day_plan is not day_plan
    assert updated_day_plan.route_options is not day_plan.route_options

    assert day_plan.route_options[0].timeline is None
    assert day_plan.route_options[1].timeline is None
    assert day_plan.route_options[2].timeline is None

    assert day_plan.route_options == original_route_options


# route_options가 비어 있으면 예외가 발생하는지 검증
def test_assign_timelines_rejects_empty_route_options():
    day_plan = make_day_plan().model_copy(
        update={
            "route_options": [],
        }
    )
    builder = TimelineOptionsBuilder()

    with pytest.raises(
        ValueError,
        match="route_options must not be empty",
    ):
        builder.assign_timelines(
            day_constraint=make_day_constraint(),
            day_plan=day_plan,
        )


# DayConstraintDTO와 DayPlanDTO의 day_index가 다르면 예외가 발생하는지 검증
def test_assign_timelines_rejects_mismatched_day_index():
    day_plan = make_day_plan().model_copy(
        update={
            "day_index": 2,
        }
    )
    builder = TimelineOptionsBuilder()

    with pytest.raises(
        ValueError,
        match="day_index must match",
    ):
        builder.assign_timelines(
            day_constraint=make_day_constraint(),
            day_plan=day_plan,
        )
