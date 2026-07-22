# Modal 환경에서 명시적인 정확 일자 배정 설정으로 TripPlannerService를 실행하는 HTTP entrypoint
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import modal
from pydantic import TypeAdapter, ValidationError

from ai.free_time_recommender.application.factory import (
    build_route_option_recommendation_generator,
)
from ai.free_time_recommender.application.plan_trip_with_recommendations import (
    GenerateRouteOptionRecommendationOutcomes,
    PlanTripWithRecommendations,
    RouteOptionRecommendationOutcome,
    TripPlanWithRecommendations,
)
from ai.free_time_recommender.config import FreeTimeRecommendationSettings
from ai.route_planner.providers.env import get_google_maps_api_key

from ai.route_planner.domain.schemas import (
    TravelMode,
)
from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)
from ai.route_planner.providers.google_routes_provider import (
    GoogleRoutesProvider,
)
from ai.route_planner.services.trip_planner_service import (
    TravelTimeMatrixProvider,
    TripPlannerService,
    TripPlannerServiceConfig,
)


# Modal에 배포할 운영용 App
app = modal.App("chiwawa-route-planner")


# Modal 컨테이너에서 사용할 Python 환경
image = (
    modal.Image.debian_slim(
        python_version="3.11",
    )
    .pip_install(
        "httpx",
        "python-dotenv",
        "pydantic",
        "fastapi",
    )
    .add_local_python_source(
        "ai",
    )
)


# Modal Dashboard의 Google Maps API Secret
google_maps_secret = modal.Secret.from_name(
    "chiwawa-google-maps",
)

# 추천 정책과 외부 호출 제한을 주입하는 비민감 운영 설정
free_time_recommendation_settings = modal.Secret.from_name(
    "chiwawa-free-time-recommendation-settings",
)


# payload를 검증하고 DRIVE 기준 정확 일자 배정 Service를 실행
def plan_trip_payload(
    payload: dict[str, Any],
    routes_provider: TravelTimeMatrixProvider,
) -> dict[str, Any]:
    request = (
        TripPlanningRequestDTO
        .model_validate(payload)
    )

    service = TripPlannerService(
        routes_provider=routes_provider,
        config=TripPlannerServiceConfig(
            day_assignment_travel_mode=(
                TravelMode.DRIVE
            ),
        ),
    )

    response = service.plan_trip(request)

    return response.model_dump(
        mode="json"
    )


def plan_trip_with_recommendations_payload(
    *,
    payload: dict[str, Any],
    routes_provider: TravelTimeMatrixProvider,
    recommendation_generator,
    settings: FreeTimeRecommendationSettings,
) -> dict[str, Any]:
    """기존 계획 응답에 날짜별 옵션 추천 결과를 추가한다."""

    request_payload = dict(payload)
    request_payload.pop("include_recommendations", None)
    request = TripPlanningRequestDTO.model_validate(request_payload)
    planner = TripPlannerService(
        routes_provider=routes_provider,
        config=TripPlannerServiceConfig(
            day_assignment_travel_mode=TravelMode.DRIVE
        ),
    )
    result = PlanTripWithRecommendations(
        trip_planner=planner,
        recommendation_generator=recommendation_generator,
    ).execute(request=request, policy=settings.policy)
    encoded = TypeAdapter(TripPlanWithRecommendations).dump_python(
        result,
        mode="json",
    )
    return {
        **encoded["planning"],
        "day_recommendations": encoded["day_recommendations"],
    }


def free_time_recommendations_payload(
    *,
    payload: dict[str, Any],
    recommendation_generator,
    settings: FreeTimeRecommendationSettings,
) -> dict[str, Any]:
    """이미 생성된 경로 옵션에 추천만 독립적으로 생성한다."""

    timezone_text = payload.get("timezone")
    route_options_payload = payload.get("route_options")
    if not isinstance(timezone_text, str) or not timezone_text.strip():
        raise ValueError("timezone은 비어 있지 않은 문자열이어야 합니다.")
    if not isinstance(route_options_payload, list):
        raise ValueError("route_options는 배열이어야 합니다.")
    from ai.route_planner.domain.trip_schemas import RouteOptionDTO

    route_options = tuple(
        RouteOptionDTO.model_validate(option)
        for option in route_options_payload
    )
    try:
        timezone = ZoneInfo(timezone_text)
    except ZoneInfoNotFoundError as error:
        raise ValueError("지원하지 않는 IANA 여행 시간대입니다.") from error
    outcomes = GenerateRouteOptionRecommendationOutcomes(
        recommendation_generator
    ).execute(
        route_options=route_options,
        timezone=timezone,
        policy=settings.policy,
    )
    return {
        "route_options": TypeAdapter(
            tuple[RouteOptionRecommendationOutcome, ...]
        ).dump_python(
            outcomes,
            mode="json",
        )
    }


# Modal HTTP Web Function
@app.function(
    image=image,
    secrets=[
        google_maps_secret,
        free_time_recommendation_settings,
    ],
    timeout=300,
)
@modal.fastapi_endpoint(
    method="POST",
    docs=True,
)
def plan_trip(
    payload: dict[str, Any],
) -> dict[str, Any]:
    routes_provider = GoogleRoutesProvider()

    try:
        include_recommendations = payload.get(
            "include_recommendations",
            False,
        )
        if not isinstance(include_recommendations, bool):
            raise ValueError(
                "include_recommendations는 boolean이어야 합니다."
            )
        if include_recommendations:
            settings = FreeTimeRecommendationSettings.from_environment()
            generator = build_route_option_recommendation_generator(
                api_key=get_google_maps_api_key(),
                settings=settings,
            )
            return plan_trip_with_recommendations_payload(
                payload=payload,
                routes_provider=routes_provider,
                recommendation_generator=generator,
                settings=settings,
            )
        return plan_trip_payload(
            payload=payload,
            routes_provider=routes_provider,
        )
    except ValidationError as error:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=error.errors(),
        ) from error
    except ValueError as error:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error


@app.function(
    image=image,
    secrets=[
        google_maps_secret,
        free_time_recommendation_settings,
    ],
    timeout=300,
)
@modal.fastapi_endpoint(method="POST", docs=True)
def free_time_recommendations(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """기존 경로 옵션을 입력받아 추천 결과만 생성하는 Endpoint."""

    try:
        settings = FreeTimeRecommendationSettings.from_environment()
        generator = build_route_option_recommendation_generator(
            api_key=get_google_maps_api_key(),
            settings=settings,
        )
        return free_time_recommendations_payload(
            payload=payload,
            recommendation_generator=generator,
            settings=settings,
        )
    except ValidationError as error:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail=error.errors()) from error
    except ValueError as error:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        from fastapi import HTTPException

        raise HTTPException(status_code=502, detail=str(error)) from error
