# 서버 관리 카테고리별 경로 주변 장소 후보 검색 Use Case
from __future__ import annotations

from dataclasses import dataclass

from ai.free_time_recommender.application.ports import AlongRoutePlaceProvider
from ai.free_time_recommender.domain.place_candidate import (
    AlongRoutePlaceSearchQuery,
    CategoryPlaceCandidates,
    DEFAULT_RECOMMENDATION_CATEGORY_CATALOG,
    PlaceCandidate,
    RecommendationCategory,
    RecommendationCategoryCatalog,
)


@dataclass(frozen=True)
class SearchAlongRoutePlacesRequest:
    """사용자 카테고리 입력이 없는 경로 주변 검색 요청."""

    encoded_polyline: str


class SearchAlongRoutePlaces:
    """카탈로그 순서로 검색하고 장소 ID 중복을 제거한다."""

    def __init__(
        self,
        *,
        provider: AlongRoutePlaceProvider,
        candidates_per_category: int,
        language_code: str,
        region_code: str,
        catalog: RecommendationCategoryCatalog = (
            DEFAULT_RECOMMENDATION_CATEGORY_CATALOG
        ),
    ) -> None:
        if (
            isinstance(candidates_per_category, bool)
            or not isinstance(candidates_per_category, int)
        ):
            raise TypeError("candidates_per_category는 정수여야 합니다.")
        if not 1 <= candidates_per_category <= 20:
            raise ValueError(
                "candidates_per_category는 1 이상 20 이하여야 합니다."
            )
        self._validate_locale_code(language_code, "language_code")
        self._validate_locale_code(region_code, "region_code")
        if language_code != "ko":
            raise ValueError(
                "language_code는 서비스 지원 언어인 ko여야 합니다."
            )
        if region_code != "JP":
            raise ValueError(
                "region_code는 서비스 지원 지역인 JP여야 합니다."
            )
        self._provider = provider
        self._candidates_per_category = candidates_per_category
        self._language_code = language_code
        self._region_code = region_code
        self._catalog = catalog

    def execute(
        self,
        request: SearchAlongRoutePlacesRequest,
    ) -> tuple[CategoryPlaceCandidates, ...]:
        """카탈로그 순서에 따라 장소 ID 중복을 제거해 반환한다."""

        if not isinstance(request, SearchAlongRoutePlacesRequest):
            raise TypeError("request는 SearchAlongRoutePlacesRequest여야 합니다.")

        seen_place_ids: set[str] = set()
        groups: list[CategoryPlaceCandidates] = []
        for definition in self._catalog.definitions:
            query = AlongRoutePlaceSearchQuery(
                encoded_polyline=request.encoded_polyline,
                category=definition.category,
                page_size=self._candidates_per_category,
                language_code=self._language_code,
                region_code=self._region_code,
            )
            searched_candidates = self._provider.search_along_route(query)
            unique_candidates = self._remove_duplicates(
                searched_candidates=searched_candidates,
                expected_category=definition.category,
                seen_place_ids=seen_place_ids,
            )
            groups.append(
                CategoryPlaceCandidates(
                    category=definition.category,
                    display_name=definition.display_name,
                    candidates=unique_candidates,
                )
            )
        return tuple(groups)

    @staticmethod
    def _remove_duplicates(
        *,
        searched_candidates: tuple[PlaceCandidate, ...],
        expected_category: RecommendationCategory,
        seen_place_ids: set[str],
    ) -> tuple[PlaceCandidate, ...]:
        if not isinstance(searched_candidates, tuple):
            raise TypeError("Provider 검색 결과는 tuple이어야 합니다.")

        unique_candidates: list[PlaceCandidate] = []
        for candidate in searched_candidates:
            if not isinstance(candidate, PlaceCandidate):
                raise TypeError(
                    "Provider 검색 결과는 PlaceCandidate만 "
                    "포함해야 합니다."
                )
            if candidate.category is not expected_category:
                raise ValueError(
                    "Provider 검색 결과의 카테고리가 요청과 "
                    "일치하지 않습니다."
                )
            if candidate.place_id in seen_place_ids:
                continue
            seen_place_ids.add(candidate.place_id)
            unique_candidates.append(candidate)
        return tuple(unique_candidates)

    @staticmethod
    def _validate_locale_code(value: str, field_name: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name}은 문자열이어야 합니다.")
        if not value.strip():
            raise ValueError(f"{field_name}은 비어 있을 수 없습니다.")
