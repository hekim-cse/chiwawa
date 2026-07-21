# 빈 시간대 일정 추천 도메인에서 사용하는 예외 정의


class FreeTimeRecommendationError(ValueError):
    """빈 시간대 일정 추천 도메인의 기본 예외."""


class InvalidAvailabilityError(FreeTimeRecommendationError):
    """하루 사용 가능 시간 범위가 올바르지 않을 때 발생."""


class InvalidBusyIntervalError(FreeTimeRecommendationError):
    """점유 시간 구간이 올바르지 않을 때 발생."""


class OverlappingBusyIntervalsError(FreeTimeRecommendationError):
    """점유 시간 구간끼리 겹칠 때 발생."""
