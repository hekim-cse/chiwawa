# 경로 최적화 결과와 빈 시간 추천 조회를 연결하는 API 계약 테스트
from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.main import create_app
from chiwawa_backend.schemas.travel import FreeTimeRecommendationResponse
from chiwawa_backend.schemas.trips import TripRead
from chiwawa_backend.state import AppState
from tests.free_time_fakes import seed_free_time_recommendation_context


@pytest.mark.anyio
async def test_latest_free_time_recommendations_use_real_route_context() -> None:
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

        response = await client.get(
            f"/api/v1/trips/{trip.id}/travel/free-time-recommendations",
        )

    assert response.status_code == HTTPStatus.OK
    result = FreeTimeRecommendationResponse.model_validate_json(response.text)
    assert result.date.isoformat() == "2026-07-10"
    assert result.items[0].place_name == "추천 전망대"
    assert result.items[0].travel_minutes == 10
    assert result.items[0].duration_minutes == 60


@pytest.mark.anyio
async def test_latest_free_time_recommendations_require_route_optimization() -> None:
    app = create_app()
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
