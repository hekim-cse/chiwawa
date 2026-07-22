# 추천 시간 예산 및 추천 가능 여부 평가 단위 테스트
from datetime import datetime, timedelta
from typing import cast

import pytest

from ai.free_time_recommender.domain.recommendation_budget import (
    CandidateTravelTimes,
    EvaluateRecommendationFeasibility,
    RecommendationFeasibility,
    RecommendationRejectionReason,
    RecommendationTimeWindow,
)
from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)


# 추천 삽입 시간 범위 생성 헬퍼
def make_window(
    *,
    available_minutes: int = 120,
) -> RecommendationTimeWindow:
    return RecommendationTimeWindow(
        day_index=1,
        start_at=datetime(2026, 8, 1, 16),
        end_at=(
            datetime(2026, 8, 1, 16)
            + timedelta(minutes=available_minutes)
        ),
        available_minutes=available_minutes,
        previous_place_id="last-poi",
        next_place_id="end",
    )


# 추천 정책 생성 헬퍼
def make_policy(
    *,
    minimum_stay_minutes: int = 60,
    maximum_one_way_travel_minutes: int = 20,
) -> RecommendationPolicy:
    return RecommendationPolicy(
        minimum_stay_minutes=minimum_stay_minutes,
        maximum_one_way_travel_minutes=(
            maximum_one_way_travel_minutes
        ),
        maximum_one_way_distance_meters=3000,
        candidate_limit=10,
    )


# 시간 예산 평가 실행 헬퍼
def evaluate(
    *,
    window: RecommendationTimeWindow | None = None,
    policy: RecommendationPolicy | None = None,
    previous_minutes: int = 15,
    next_minutes: int = 15,
) -> RecommendationFeasibility:
    return EvaluateRecommendationFeasibility().evaluate(
        window=window or make_window(),
        policy=policy or make_policy(),
        travel_times=CandidateTravelTimes(
            previous_to_candidate_minutes=previous_minutes,
            candidate_to_next_minutes=next_minutes,
        ),
    )


# 편도 상한과 전체 시간 예산을 만족하는 후보 허용 검증
def test_evaluate_accepts_candidate_within_all_time_limits() -> None:
    result = evaluate()

    assert result.is_recommendable is True
    assert result.required_minutes == 90
    assert result.remaining_minutes == 30
    assert result.rejection_reasons == ()


# 편도 상한 및 전체 시간 예산과 정확히 같은 경계값 허용 검증
def test_evaluate_accepts_exact_total_and_one_way_limits() -> None:
    result = evaluate(
        window=make_window(available_minutes=100),
        previous_minutes=20,
        next_minutes=20,
    )

    assert result.is_recommendable is True
    assert result.required_minutes == 100
    assert result.remaining_minutes == 0


# 양쪽 편도 상한 초과 사유의 개별 반환 검증
def test_evaluate_reports_each_exceeded_one_way_limit() -> None:
    result = evaluate(
        window=make_window(available_minutes=200),
        previous_minutes=21,
        next_minutes=22,
    )

    assert result.is_recommendable is False
    assert result.rejection_reasons == (
        RecommendationRejectionReason
        .PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED,
        RecommendationRejectionReason
        .CANDIDATE_TO_NEXT_LIMIT_EXCEEDED,
    )


# 이동시간과 최소 체류시간의 합이 전체 예산을 초과하는 경우 검증
def test_evaluate_reports_insufficient_total_time() -> None:
    result = evaluate(
        window=make_window(available_minutes=89),
    )

    assert result.is_recommendable is False
    assert result.remaining_minutes == -1
    assert result.rejection_reasons == (
        RecommendationRejectionReason.INSUFFICIENT_TOTAL_TIME,
    )


# 편도 상한 0분 정책의 실제 이동시간 제한 검증
def test_zero_travel_limit_allows_only_zero_minute_legs() -> None:
    policy = make_policy(maximum_one_way_travel_minutes=0)

    accepted = evaluate(
        policy=policy,
        previous_minutes=0,
        next_minutes=0,
    )
    rejected = evaluate(
        policy=policy,
        previous_minutes=1,
        next_minutes=0,
    )

    assert accepted.is_recommendable is True
    assert rejected.rejection_reasons == (
        RecommendationRejectionReason
        .PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED,
    )


# 후보 이동시간의 음수·불리언·비정수 입력 거부 검증
@pytest.mark.parametrize(
    "field_name",
    [
        "previous_to_candidate_minutes",
        "candidate_to_next_minutes",
    ],
)
@pytest.mark.parametrize("invalid_value", [-1, True, 1.5])
def test_candidate_travel_times_reject_invalid_values(
    field_name: str,
    invalid_value: object,
) -> None:
    # 기본 양쪽 편도 이동시간 구성
    values = {
        "previous_to_candidate_minutes": 10,
        "candidate_to_next_minutes": 10,
    }

    # 검증 대상 필드에 잘못된 값 주입
    values[field_name] = cast(int, invalid_value)

    # 값 범위와 타입에 따른 명시적 예외 검증
    expected_exception = (
        ValueError if invalid_value == -1 else TypeError
    )
    with pytest.raises(expected_exception):
        CandidateTravelTimes(**values)
