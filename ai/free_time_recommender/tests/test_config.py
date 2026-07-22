# 빈 시간대 추천 운영 환경변수 설정 테스트
import pytest

from ai.free_time_recommender.config import FreeTimeRecommendationSettings


def valid_environment() -> dict[str, str]:
    return {
        "FREE_TIME_MINIMUM_STAY_MINUTES": "30",
        "FREE_TIME_MAXIMUM_ONE_WAY_TRAVEL_MINUTES": "20",
        "FREE_TIME_MAXIMUM_ONE_WAY_DISTANCE_METERS": "3000",
        "FREE_TIME_CANDIDATES_PER_CATEGORY": "3",
        "FREE_TIME_CANDIDATES_TO_EVALUATE_PER_CATEGORY": "2",
        "FREE_TIME_PROVIDER_TIMEOUT_SECONDS": "20",
    }


# 확정한 초기 운영값을 정책과 외부 호출 설정으로 변환
def test_settings_load_explicit_initial_policy() -> None:
    settings = FreeTimeRecommendationSettings.from_environment(
        valid_environment()
    )

    assert settings.minimum_stay_minutes == 30
    assert settings.candidates_per_category == 3
    assert settings.provider_timeout_seconds == 20
    assert settings.policy.minimum_stay_minutes == 30
    assert settings.policy.candidate_limit == 2


# 누락된 설정을 임의 기본값으로 대체하지 않고 시작 단계에서 거부
def test_settings_reject_missing_environment_value() -> None:
    values = valid_environment()
    del values["FREE_TIME_MINIMUM_STAY_MINUTES"]

    with pytest.raises(ValueError, match="필수 환경변수"):
        FreeTimeRecommendationSettings.from_environment(values)
