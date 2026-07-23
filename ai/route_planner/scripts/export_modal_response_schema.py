# Backend에 전달할 Modal 통합 응답 JSON Schema 생성 스크립트
from __future__ import annotations

import json
from pathlib import Path

from ai.free_time_recommender.adapters.modal_response import (
    TripPlanningWithRecommendationsResponseDTO,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "contracts"
    / "ai_route_planner"
    / "trip_planning_with_recommendations_response.schema.json"
)


def build_schema() -> dict[str, object]:
    """현재 통합 응답 DTO의 JSON Schema를 반환한다."""

    return TripPlanningWithRecommendationsResponseDTO.model_json_schema()


def main() -> None:
    """계약 디렉터리에 결정적인 형식으로 Schema를 기록한다."""

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            build_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
