# 경로 최적화 결과와 빈 시간 추천 조회를 연결하는 API 계약 테스트
from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.ai_planning import (
    RecommendationCategory,
    RecommendationGroupRead,
)
from chiwawa_backend.schemas.travel import FreeTimeRecommendationResponse
from chiwawa_backend.schemas.trips import TripRead
from chiwawa_backend.state import AppState
from tests.free_time_fakes import (
    FakeFreeTimeRoutePlanner,
    seed_free_time_recommendation_context,
)


@pytest.mark.anyio
async def test_latest_free_time_recommendations_use_real_route_context() -> None:
    state = AppState()
    planner: FakeFreeTimeRoutePlanner | None = None
    app = create_app(state)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Paris",
                "country": "France",
                "start_date": "2026-07-10",
                "end_date": "2026-07-10",
            },
        )
        trip = TripRead.model_validate_json(trip_response.text)
        seed_free_time_recommendation_context(state, trip.id)
        planner = FakeFreeTimeRoutePlanner(state, trip.id)
        app = create_app(state, route_planner=planner)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations",
        )

    assert response.status_code == HTTPStatus.OK
    result = FreeTimeRecommendationResponse.model_validate_json(response.text)
    assert result.date.isoformat() == "2026-07-10"
    assert result.items[0].place_name == "추천 전망대"
    assert result.items[0].travel_minutes == 10
    assert result.items[0].duration_minutes == 60
    assert result.items[0].recommendation.candidate.place_id == "google-test-landmark"
    assert planner is not None
    assert planner.calls == 1


@pytest.mark.anyio
async def test_latest_free_time_recommendations_preserve_every_category_item() -> None:
    """Modal의 카테고리별 후보를 축소하지 않고 모두 반환한다."""
    state = AppState()
    app = create_app(state)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Paris",
                "country": "France",
                "start_date": "2026-07-10",
                "end_date": "2026-07-10",
            },
        )
    trip = TripRead.model_validate_json(trip_response.text)
    seed_free_time_recommendation_context(state, trip.id)
    route_key = (trip.id, 1)
    landmark = state.issued_route_recommendations[route_key][0]
    first = landmark.recommendations[0]
    second = first.model_copy(
        update={
            "candidate": first.candidate.model_copy(
                update={
                    "place_id": "google-test-landmark-2",
                    "name": "추천 성당",
                }
            )
        }
    )
    cafe_first = first.model_copy(
        update={
            "candidate": first.candidate.model_copy(
                update={
                    "place_id": "google-test-cafe-1",
                    "name": "추천 카페 A",
                    "category": RecommendationCategory.CAFE,
                }
            )
        }
    )
    cafe_second = cafe_first.model_copy(
        update={
            "candidate": cafe_first.candidate.model_copy(
                update={
                    "place_id": "google-test-cafe-2",
                    "name": "추천 카페 B",
                }
            )
        }
    )
    state.issued_route_recommendations[route_key] = [
        landmark.model_copy(update={"recommendations": [first, second]}),
        RecommendationGroupRead(
            category=RecommendationCategory.CAFE,
            display_name="카페",
            recommendations=[cafe_first, cafe_second],
        ),
    ]
    planner = FakeFreeTimeRoutePlanner(state, trip.id)
    app = create_app(state, route_planner=planner)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations",
        )

    result = FreeTimeRecommendationResponse.model_validate_json(response.text)
    assert [item.title for item in result.items] == [
        "랜드마크·관광명소",
        "랜드마크·관광명소",
        "카페",
        "카페",
    ]


@pytest.mark.anyio
async def test_latest_free_time_recommendations_require_route_optimization() -> None:
    state = AppState()
    planner = FakeFreeTimeRoutePlanner(state, "unused")
    app = create_app(state, route_planner=planner)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        trip_response = await client.post(
            "/api/v1/trips",
            json={
                "city": "Paris",
                "country": "France",
                "start_date": "2026-07-10",
                "end_date": "2026-07-10",
            },
        )
        trip = TripRead.model_validate_json(trip_response.text)

        response = await client.get(
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations",
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "경로 최적화" in response.json()["detail"]
