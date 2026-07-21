# Route Planner Timeline을 빈 시간 추천 도메인으로 변환할 때 사용하는 예외


class RoutePlannerTimelineAdapterError(ValueError):
    """
    Route Planner Timeline의 값이 올바르지 않거나
    빈 시간 추천 도메인으로 안전하게 변환할 수 없을 때 발생한다.
    """
