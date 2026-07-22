# 최초 일정에 함께 표시할 삽입 가능 추천 그룹 생성 Use Case
from __future__ import annotations

from dataclasses import dataclass

from ai.free_time_recommender.application.ports import (
    CandidateRouteMetricsProvider,
)
from ai.free_time_recommender.domain.candidate_route_metrics import (
    CandidateRouteMetrics,
    CandidateRouteMetricsQuery,
)
from ai.free_time_recommender.domain.place_candidate import (
    CategoryRouteLegPlaceCandidates,
    PlaceCandidate,
    RecommendationCategory,
    RouteLegPlaceCandidate,
)
from ai.free_time_recommender.domain.recommendation_budget import (
    CandidateTravelTimes,
)
from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)
from ai.free_time_recommender.domain.route_geometry import RouteTravelMode
from ai.free_time_recommender.domain.route_insertion import (
    CandidateInsertionSchedule,
    EvaluateRouteLegInsertionImpact,
    RouteLegInsertionImpact,
    RouteLegInsertionWindow,
)


@dataclass(frozen=True)
class InsertableCandidateRecommendation:
    """후보와 가장 영향이 작은 삽입 위치 및 계산 결과."""

    candidate: PlaceCandidate
    window: RouteLegInsertionWindow
    route_metrics: CandidateRouteMetrics
    insertion_impact: RouteLegInsertionImpact


@dataclass(frozen=True)
class InitialRecommendationGroup:
    """최초 일정과 함께 표시할 한 카테고리의 추천 후보."""

    category: RecommendationCategory
    display_name: str
    recommendations: tuple[InsertableCandidateRecommendation, ...]


@dataclass(frozen=True)
class GenerateInitialRecommendationGroupsRequest:
    """장소 후보와 기존 일정 삽입 구간을 연결하는 요청."""

    candidate_groups: tuple[CategoryRouteLegPlaceCandidates, ...]
    insertion_windows: tuple[RouteLegInsertionWindow, ...]
    travel_mode: RouteTravelMode
    policy: RecommendationPolicy


class GenerateInitialRecommendationGroups:
    """카테고리별 상위 후보 중 삽입 가능한 결과만 반환한다."""

    def __init__(
        self,
        *,
        route_metrics_provider: CandidateRouteMetricsProvider,
        candidates_to_evaluate_per_category: int,
    ) -> None:
        # 외부 API 호출 수를 제한하는 운영 설정이므로
        # boolean이나 0 이하 값을 허용하지 않는다.
        if (
            isinstance(candidates_to_evaluate_per_category, bool)
            or not isinstance(candidates_to_evaluate_per_category, int)
        ):
            raise TypeError(
                "candidates_to_evaluate_per_category는 정수여야 합니다."
            )
        if candidates_to_evaluate_per_category <= 0:
            raise ValueError(
                "candidates_to_evaluate_per_category는 1 이상이어야 합니다."
            )
        self._route_metrics_provider = route_metrics_provider
        self._candidate_limit = candidates_to_evaluate_per_category
        self._evaluator = EvaluateRouteLegInsertionImpact()

    def execute(
        self,
        request: GenerateInitialRecommendationGroupsRequest,
    ) -> tuple[InitialRecommendationGroup, ...]:
        """후보별 최소 추가시간 삽입 구간을 선택한다."""

        if not isinstance(
            request,
            GenerateInitialRecommendationGroupsRequest,
        ):
            raise TypeError(
                "request는 GenerateInitialRecommendationGroupsRequest여야 합니다."
            )

        # ------------------------------------------------------------
        # 1단계: 장소 검색 Provider가 반환한 카테고리 순서를 유지한다.
        # ------------------------------------------------------------
        groups: list[InitialRecommendationGroup] = []
        for candidate_group in request.candidate_groups:
            # --------------------------------------------------------
            # 2단계: Google 호출 비용을 통제하기 위해 각 카테고리의
            # 검색 상위 후보만 실제 경로 삽입 평가 대상으로 사용한다.
            # --------------------------------------------------------
            recommendations = []
            for routed_candidate in candidate_group.candidates[
                : self._candidate_limit
            ]:
                window = self._find_matching_window(
                    routed_candidate,
                    request.insertion_windows,
                )
                recommendation = self._evaluate_insertion(
                    candidate=routed_candidate.candidate,
                    window=window,
                    travel_mode=request.travel_mode,
                    policy=request.policy,
                )
                if recommendation is not None:
                    recommendations.append(recommendation)

            # --------------------------------------------------------
            # 3단계: 삽입 가능한 후보가 없는 카테고리는 화면에
            # 빈 추천 영역으로 노출하지 않고 결과에서 제외한다.
            # --------------------------------------------------------
            if recommendations:
                groups.append(
                    InitialRecommendationGroup(
                        category=candidate_group.category,
                        display_name=candidate_group.display_name,
                        recommendations=tuple(recommendations),
                    )
                )

        # ------------------------------------------------------------
        # 4단계: API 조합 계층이 기존 Timeline과 함께 반환할
        # 카테고리별 추천 그룹을 불변 tuple로 제공한다.
        # ------------------------------------------------------------
        return tuple(groups)

    @staticmethod
    def _find_matching_window(
        routed_candidate: RouteLegPlaceCandidate,
        windows: tuple[RouteLegInsertionWindow, ...],
    ) -> RouteLegInsertionWindow:
        matches = tuple(
            window
            for window in windows
            if window.day_index == routed_candidate.day_index
            and window.leg_index == routed_candidate.leg_index
            and window.previous_place_id == routed_candidate.origin_place_id
            and window.next_place_id == routed_candidate.destination_place_id
        )
        if not matches:
            raise ValueError(
                "후보의 경로 구간과 일치하는 삽입 Window가 없습니다."
            )
        if len(matches) > 1:
            raise ValueError(
                "후보의 경로 구간과 일치하는 삽입 Window가 중복됩니다."
            )
        return matches[0]

    def _evaluate_insertion(
        self,
        *,
        candidate: PlaceCandidate,
        window: RouteLegInsertionWindow,
        travel_mode: RouteTravelMode,
        policy: RecommendationPolicy,
    ) -> InsertableCandidateRecommendation | None:
        # 기존 최적화 일정에 이미 포함된 장소 ID를 수집한다.
        # 기존 방문지를 다시 추천하거나 동일 장소 경로를 조회하지 않는다.
        if candidate.place_id in (
            window.previous_place_id,
            window.next_place_id,
        ):
            return None

        # 후보가 검색된 실제 구간만 평가해 불필요한 Routes 호출을 막는다.
        # Provider 오류는 숨기지 않고 호출자에게 그대로 전달한다.
        metrics = self._route_metrics_provider.get_candidate_route_metrics(
            CandidateRouteMetricsQuery(
                previous_place_id=window.previous_place_id,
                candidate_place_id=candidate.place_id,
                next_place_id=window.next_place_id,
                previous_departure_at=window.previous_departure_at,
                stay_minutes=policy.minimum_stay_minutes,
                travel_mode=travel_mode,
            )
        )

        # 외부 이동 지표를 순수 도메인 평가 입력으로 변환한다.
        impact = self._evaluator.evaluate(
            window=window,
            policy=policy,
            candidate_schedule=CandidateInsertionSchedule(
                travel_times=CandidateTravelTimes(
                    previous_to_candidate_minutes=(
                        metrics.previous_to_candidate.travel_minutes
                    ),
                    candidate_to_next_minutes=(
                        metrics.candidate_to_next.travel_minutes
                    ),
                ),
                previous_to_candidate_distance_meters=(
                    metrics.previous_to_candidate.distance_meters
                ),
                candidate_to_next_distance_meters=(
                    metrics.candidate_to_next.distance_meters
                ),
                stay_minutes=policy.minimum_stay_minutes,
            ),
        )

        # 시간·거리·종료시각 정책을 모두 만족한 후보만 반환한다.
        if not impact.is_insertable:
            return None
        return InsertableCandidateRecommendation(
            candidate=candidate,
            window=window,
            route_metrics=metrics,
            insertion_impact=impact,
        )
