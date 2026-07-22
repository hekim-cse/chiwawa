# 최초 일정의 카테고리별 삽입 가능 추천 그룹 테스트
from datetime import datetime, timedelta, timezone

from ai.free_time_recommender.application.generate_initial_recommendation_groups import (
    GenerateInitialRecommendationGroups,
    GenerateInitialRecommendationGroupsRequest,
)
from ai.free_time_recommender.domain.candidate_route_metrics import (
    CandidateRouteMetrics,
    CandidateRouteMetricsQuery,
    RouteLegMetrics,
)
from ai.free_time_recommender.domain.place_candidate import (
    CategoryRouteLegPlaceCandidates,
    PlaceCandidate,
    RecommendationCategory,
    RouteLegPlaceCandidate,
)
from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)
from ai.free_time_recommender.domain.route_geometry import (
    GeoCoordinate,
    RouteTravelMode,
)
from ai.free_time_recommender.domain.route_insertion import (
    RouteLegInsertionWindow,
)


class StubRouteMetricsProvider:
    """이전 장소별 고정 이동시간을 반환하는 테스트 Provider."""

    # 구간별 이동시간 설정과 실제 조회 조건 기록
    def __init__(self, minutes_by_previous: dict[str, int]) -> None:
        self.minutes_by_previous = minutes_by_previous
        self.queries: list[CandidateRouteMetricsQuery] = []

    def get_candidate_route_metrics(
        self,
        query: CandidateRouteMetricsQuery,
    ) -> CandidateRouteMetrics:
        # Use Case가 생성한 쿼리를 보존해 호출 횟수와 입력을 검증한다.
        self.queries.append(query)

        # 이전 장소에 따라 서로 다른 추가시간이 계산되도록 구성한다.
        minutes = self.minutes_by_previous[query.previous_place_id]
        arrival = query.previous_departure_at + timedelta(minutes=minutes)
        departure = arrival + timedelta(minutes=query.stay_minutes)
        return CandidateRouteMetrics(
            previous_to_candidate=RouteLegMetrics(minutes, 1000),
            candidate_to_next=RouteLegMetrics(minutes, 1000),
            candidate_arrival_at=arrival,
            candidate_departure_at=departure,
            next_arrival_at=departure + timedelta(minutes=minutes),
        )


# 일본 표준시 기반 테스트 시각 생성 헬퍼
def at(hour: int) -> datetime:
    return datetime(2026, 8, 1, hour, tzinfo=timezone(timedelta(hours=9)))


# 기존 Timeline의 한 이동 구간 생성 헬퍼
def make_window(leg_index: int, previous_id: str) -> RouteLegInsertionWindow:
    return RouteLegInsertionWindow(
        day_index=1,
        leg_index=leg_index,
        previous_place_id=previous_id,
        next_place_id=f"next-{leg_index}",
        previous_departure_at=at(10 + leg_index),
        next_arrival_at=at(10 + leg_index) + timedelta(minutes=20),
        original_travel_minutes=20,
        original_timeline_end_at=at(15),
        planned_end_at=at(18),
    )


def make_group(
    candidate: PlaceCandidate,
    *,
    leg_index: int,
    previous_id: str,
) -> CategoryRouteLegPlaceCandidates:
    return CategoryRouteLegPlaceCandidates(
        category=candidate.category,
        display_name="랜드마크·관광명소",
        candidates=(
            RouteLegPlaceCandidate(
                candidate=candidate,
                day_index=1,
                leg_index=leg_index,
                origin_place_id=previous_id,
                destination_place_id=f"next-{leg_index}",
            ),
        ),
    )


# 후보가 검색된 원래 구간만 평가하는지 검증
def test_execute_evaluates_only_candidate_source_window() -> None:
    provider = StubRouteMetricsProvider({"previous-0": 15, "previous-1": 10})
    candidate = PlaceCandidate(
        place_id="도쿄타워-place-id",
        name="도쿄 타워",
        coordinate=GeoCoordinate(35.6586, 139.7454),
        category=RecommendationCategory.LANDMARK,
    )
    policy = RecommendationPolicy(
        minimum_stay_minutes=60,
        maximum_one_way_travel_minutes=30,
        maximum_one_way_distance_meters=3000,
        candidate_limit=5,
    )

    result = GenerateInitialRecommendationGroups(
        route_metrics_provider=provider,
        candidates_to_evaluate_per_category=1,
    ).execute(
        GenerateInitialRecommendationGroupsRequest(
            candidate_groups=(
                make_group(candidate, leg_index=1, previous_id="previous-1"),
            ),
            insertion_windows=(
                make_window(0, "previous-0"),
                make_window(1, "previous-1"),
            ),
            travel_mode=RouteTravelMode.TRANSIT,
            policy=policy,
        )
    )

    recommendation = result[0].recommendations[0]

    # 검색된 두 번째 구간만 조회해 후보별 API 호출 수를 제한한다.
    assert recommendation.window.leg_index == 1
    assert recommendation.insertion_impact.additional_minutes == 60
    assert len(provider.queries) == 1


# 시간 정책을 만족하지 못한 카테고리를 결과에서 제외하는지 검증
def test_execute_omits_category_without_insertable_candidate() -> None:
    provider = StubRouteMetricsProvider({"previous-0": 40})
    candidate = PlaceCandidate(
        place_id="도쿄타워-place-id",
        name="도쿄 타워",
        coordinate=GeoCoordinate(35.6586, 139.7454),
        category=RecommendationCategory.LANDMARK,
    )
    policy = RecommendationPolicy(60, 30, 3000, 5)

    result = GenerateInitialRecommendationGroups(
        route_metrics_provider=provider,
        candidates_to_evaluate_per_category=1,
    ).execute(
        GenerateInitialRecommendationGroupsRequest(
            candidate_groups=(
                make_group(candidate, leg_index=0, previous_id="previous-0"),
            ),
            insertion_windows=(make_window(0, "previous-0"),),
            travel_mode=RouteTravelMode.TRANSIT,
            policy=policy,
        )
    )

    assert result == ()


# 기존 일정에 이미 포함된 장소를 API 호출 전에 제외하는지 검증
def test_execute_skips_place_already_in_original_route() -> None:
    provider = StubRouteMetricsProvider({"previous-0": 10})
    existing_candidate = PlaceCandidate(
        place_id="previous-0",
        name="기존 장소",
        coordinate=GeoCoordinate(35.6812, 139.7671),
        category=RecommendationCategory.LANDMARK,
    )
    policy = RecommendationPolicy(60, 30, 3000, 5)

    result = GenerateInitialRecommendationGroups(
        route_metrics_provider=provider,
        candidates_to_evaluate_per_category=1,
    ).execute(
        GenerateInitialRecommendationGroupsRequest(
            candidate_groups=(
                make_group(
                    existing_candidate,
                    leg_index=0,
                    previous_id="previous-0",
                ),
            ),
            insertion_windows=(make_window(0, "previous-0"),),
            travel_mode=RouteTravelMode.TRANSIT,
            policy=policy,
        )
    )

    assert result == ()

    # 동일 장소 후보는 이동 지표 Provider를 호출하지 않아 비용이 들지 않는다.
    assert provider.queries == []
