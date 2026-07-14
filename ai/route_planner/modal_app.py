# Modal 환경에서 TripPlannerService를 실행하는 HTTP entrypoint
from typing import Any

import modal
from pydantic import ValidationError

from ai.route_planner.domain.trip_schemas import (
    TripPlanningRequestDTO,
)
from ai.route_planner.providers.google_routes_provider import (
    GoogleRoutesProvider,
)
from ai.route_planner.services.trip_planner_service import (
    TravelTimeMatrixProvider,
    TripPlannerService,
)


# Modal에 배포할 운영용 App
app = modal.App("chiwawa-route-planner")


# Modal 컨테이너에서 사용할 Python 환경
# Modal 1.0 이후 로컬 패키지를 명시적으로 포함해야 하므로 ai 패키지를 추가
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


# Modal Dashboard의 Secrets에 등록할 Secret 이름
google_maps_secret = modal.Secret.from_name(
    "chiwawa-google-maps",
)


# payload를 검증하고 TripPlannerService를 실행하는 순수 Python 함수
# 테스트에서는 Fake Provider를 주입해 실제 Google API 호출 없이 검증 가능
def plan_trip_payload(
    payload: dict[str, Any],
    routes_provider: TravelTimeMatrixProvider,
) -> dict[str, Any]:
    request = TripPlanningRequestDTO.model_validate(
        payload
    )

    service = TripPlannerService(
        routes_provider=routes_provider,
    )

    response = service.plan_trip(
        request
    )

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
    # Secret으로 주입된 GOOGLE_MAPS_API_KEY를 사용하는 실제 Provider
    routes_provider = GoogleRoutesProvider()

    try:
        return plan_trip_payload(
            payload=payload,
            routes_provider=routes_provider,
        )
    except ValidationError as error:
        # FastAPI가 올바른 HTTP 상태를 반환하도록 endpoint 계층에서 변환
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
