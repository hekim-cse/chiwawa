# Modal 환경에서 명시적인 정확 일자 배정 설정으로 TripPlannerService를 실행하는 HTTP entrypoint
from typing import Any

import modal
from pydantic import ValidationError

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


# Modal HTTP Web Function
@app.function(
    image=image,
    secrets=[
        google_maps_secret,
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
