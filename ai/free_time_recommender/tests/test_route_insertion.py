# 경로 구간별 추천 장소 삽입 영향 평가 단위 테스트
from datetime import datetime, timedelta
from typing import cast

import pytest

from ai.free_time_recommender.domain.recommendation_budget import (
    CandidateTravelTimes,
)
from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)
from ai.free_time_recommender.domain.route_insertion import (
    CandidateInsertionSchedule,
    EvaluateRouteLegInsertionImpact,
    RouteInsertionRejectionReason,
    RouteLegInsertionImpact,
    RouteLegInsertionWindow,
)


# 테스트 시각 생성 헬퍼
def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 1, hour, minute)


# 경로 구간 생성 헬퍼
def make_window(
    *,
    original_travel_minutes: int = 20,
    original_timeline_end_at: datetime | None = None,
    planned_end_at: datetime | None = None,
) -> RouteLegInsertionWindow:
    return RouteLegInsertionWindow(
        day_index=1,
        leg_index=1,
        previous_place_id="poi-a",
        next_place_id="poi-b",
        previous_departure_at=at(12),
        next_arrival_at=(
            at(12) + timedelta(minutes=original_travel_minutes)
        ),
        original_travel_minutes=original_travel_minutes,
        original_timeline_end_at=(
            original_timeline_end_at or at(17)
        ),
        planned_end_at=planned_end_at or at(18),
    )


# 추천 정책 생성 헬퍼
def make_policy(
    *,
    minimum_stay_minutes: int = 30,
    maximum_one_way_travel_minutes: int = 20,
) -> RecommendationPolicy:
    return RecommendationPolicy(
        minimum_stay_minutes=minimum_stay_minutes,
        maximum_one_way_travel_minutes=(
            maximum_one_way_travel_minutes
        ),
        maximum_distance_meters=3000,
        candidate_limit=10,
    )


# 후보 삽입 영향 평가 헬퍼
def evaluate(
    *,
    window: RouteLegInsertionWindow | None = None,
    policy: RecommendationPolicy | None = None,
    previous_minutes: int = 10,
    next_minutes: int = 15,
    stay_minutes: int = 30,
) -> RouteLegInsertionImpact:
    return EvaluateRouteLegInsertionImpact().evaluate(
        window=window or make_window(),
        policy=policy or make_policy(),
        candidate_schedule=CandidateInsertionSchedule(
            travel_times=CandidateTravelTimes(
                previous_to_candidate_minutes=previous_minutes,
                candidate_to_next_minutes=next_minutes,
            ),
            stay_minutes=stay_minutes,
        ),
    )


# 기존 이동 구간을 후보 경유 구간으로 교체한 시간 영향 검증
def test_evaluate_calculates_route_insertion_impact() -> None:
    result = evaluate()

    assert result.replacement_travel_minutes == 25
    assert result.replacement_total_minutes == 55
    assert result.additional_minutes == 35
    assert result.updated_next_arrival_at == at(12, 55)
    assert result.updated_timeline_end_at == at(17, 35)
    assert result.remaining_minutes == 25
    assert result.is_insertable is True
    assert result.rejection_reasons == ()


# 변경 일정이 계획 종료와 정확히 같으면 삽입 허용 검증
def test_evaluate_accepts_updated_end_equal_to_planned_end() -> None:
    result = evaluate(
        window=make_window(
            original_timeline_end_at=at(17),
            planned_end_at=at(17, 35),
        )
    )

    assert result.updated_timeline_end_at == at(17, 35)
    assert result.remaining_minutes == 0
    assert result.is_insertable is True


# 후보 경유 후 전체 일정이 계획 종료를 초과하는 경우 검증
def test_evaluate_reports_planned_end_exceeded() -> None:
    result = evaluate(
        window=make_window(
            original_timeline_end_at=at(17),
            planned_end_at=at(17, 34),
        )
    )

    assert result.remaining_minutes == -1
    assert result.rejection_reasons == (
        RouteInsertionRejectionReason.PLANNED_END_EXCEEDED,
    )


# 기존보다 짧은 후보 경유 경로의 음수 추가시간 유지 검증
def test_evaluate_preserves_negative_additional_minutes() -> None:
    result = evaluate(
        window=make_window(original_travel_minutes=60),
        previous_minutes=5,
        next_minutes=5,
        stay_minutes=30,
    )

    assert result.replacement_total_minutes == 40
    assert result.additional_minutes == -20
    assert result.updated_next_arrival_at == at(12, 40)
    assert result.updated_timeline_end_at == at(16, 40)


# 최소 체류시간과 양쪽 편도 상한의 개별 실패 사유 검증
def test_evaluate_reports_all_policy_rejection_reasons() -> None:
    result = evaluate(
        window=make_window(planned_end_at=at(20)),
        previous_minutes=21,
        next_minutes=22,
        stay_minutes=29,
    )

    assert result.rejection_reasons == (
        RouteInsertionRejectionReason.STAY_DURATION_BELOW_MINIMUM,
        RouteInsertionRejectionReason
        .PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED,
        RouteInsertionRejectionReason
        .CANDIDATE_TO_NEXT_LIMIT_EXCEEDED,
    )


# 후보 체류시간의 잘못된 타입과 범위 거부 검증
@pytest.mark.parametrize("invalid_value", [0, -1, True, 1.5])
def test_candidate_schedule_rejects_invalid_stay_minutes(
    invalid_value: object,
) -> None:
    expected_exception = (
        ValueError
        if invalid_value in (0, -1)
        else TypeError
    )

    with pytest.raises(expected_exception):
        CandidateInsertionSchedule(
            travel_times=CandidateTravelTimes(
                previous_to_candidate_minutes=10,
                candidate_to_next_minutes=10,
            ),
            stay_minutes=cast(int, invalid_value),
        )


# 기존 이동시간과 실제 구간 길이 불일치 거부 검증
def test_window_rejects_original_travel_time_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="실제 시간과 일치",
    ):
        RouteLegInsertionWindow(
            day_index=1,
            leg_index=0,
            previous_place_id="start",
            next_place_id="poi-a",
            previous_departure_at=at(10),
            next_arrival_at=at(10, 20),
            original_travel_minutes=19,
            original_timeline_end_at=at(17),
            planned_end_at=at(18),
        )
