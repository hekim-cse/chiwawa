import itertools
from typing import Dict, List, Tuple

import modal
from pydantic import BaseModel, Field


app = modal.App("chiwawa-route-planner-demo")

image = modal.Image.debian_slim().pip_install("pydantic", "fastapi[standard]")


class RouteRequest(BaseModel):
    start: str
    places: List[str] = Field(min_length=1, max_length=6)


class RouteResponse(BaseModel):
    route: List[str]
    total_minutes: int


# Modal 배포 테스트용 임시 이동 시간 행렬
# 실제 서비스에서는 Google Routes API Provider가 이 데이터를 생성하게 됨
STATIC_TRAVEL_TIME_MATRIX: Dict[Tuple[str, str], int] = {
    ("난바역", "도톤보리"): 8,
    ("도톤보리", "난바역"): 8,
    ("난바역", "오사카성"): 25,
    ("오사카성", "난바역"): 25,
    ("난바역", "우메다 스카이빌딩"): 18,
    ("우메다 스카이빌딩", "난바역"): 18,
    ("도톤보리", "오사카성"): 28,
    ("오사카성", "도톤보리"): 28,
    ("도톤보리", "우메다 스카이빌딩"): 20,
    ("우메다 스카이빌딩", "도톤보리"): 20,
    ("오사카성", "우메다 스카이빌딩"): 22,
    ("우메다 스카이빌딩", "오사카성"): 22,
}


def calculate_total_minutes(route: List[str]) -> int:
    total_minutes = 0

    for current_place, next_place in zip(route, route[1:]):
        key = (current_place, next_place)

        if key not in STATIC_TRAVEL_TIME_MATRIX:
            raise ValueError(f"Missing travel time: {current_place} -> {next_place}")

        total_minutes += STATIC_TRAVEL_TIME_MATRIX[key]

    return total_minutes


def optimize_small_route(start: str, places: List[str]) -> RouteResponse:
    best_route: List[str] | None = None
    best_minutes: int | None = None

    for candidate_order in itertools.permutations(places):
        route = [start, *candidate_order]
        total_minutes = calculate_total_minutes(route)

        if best_minutes is None or total_minutes < best_minutes:
            best_route = route
            best_minutes = total_minutes

    if best_route is None or best_minutes is None:
        raise ValueError("No route candidate was generated")

    return RouteResponse(
        route=best_route,
        total_minutes=best_minutes,
    )


@app.function(image=image)
@modal.fastapi_endpoint(method="POST")
def optimize_route(payload: dict) -> dict:
    request = RouteRequest(**payload)

    result = optimize_small_route(
        start=request.start,
        places=request.places,
    )

    return result.model_dump()
