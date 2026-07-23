from collections.abc import Callable

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from chiwawa_backend.config import get_settings
from chiwawa_backend.dependencies import get_photo_place_recognizer, get_state
from chiwawa_backend.errors import (
    ConfigurationError,
    DomainValidationError,
    NotFoundError,
    UpstreamServiceError,
)
from chiwawa_backend.routers import (
    assistant,
    auth,
    health,
    memorial,
    photo_places,
    plans,
    schedule,
    travel,
    trips,
    wanted_places,
)
from chiwawa_backend.schemas.base import ErrorResponse
from chiwawa_backend.services.photo_places import PhotoPlaceRecognizer
from chiwawa_backend.state import AppState


def create_app(
    state: AppState | None = None,
    photo_place_recognizer: PhotoPlaceRecognizer | None = None,
) -> FastAPI:
    app_state = state or AppState()
    app = FastAPI(
        title="Chiwawa Backend",
        description="AI 기반 일본 자유여행 일정 추천 및 관리 API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_api_route(
        "/",
        redirect_to_swagger_ui,
        methods=["GET"],
        include_in_schema=False,
    )
    app.dependency_overrides[get_state] = _state_dependency(app_state)
    if photo_place_recognizer is not None:
        app.dependency_overrides[get_photo_place_recognizer] = _recognizer_dependency(
            photo_place_recognizer
        )
    _register_exception_handlers(app)
    for router in (
        health.router,
        auth.router,
        trips.router,
        photo_places.router,
        wanted_places.router,
        plans.router,
        schedule.router,
        travel.router,
        assistant.router,
        memorial.router,
        memorial.album_router,
    ):
        app.include_router(router)
    return app


def _state_dependency(state: AppState) -> Callable[[], AppState]:
    def dependency() -> AppState:
        return state

    return dependency


def _recognizer_dependency(
    recognizer: PhotoPlaceRecognizer,
) -> Callable[[], PhotoPlaceRecognizer]:
    def dependency() -> PhotoPlaceRecognizer:
        return recognizer

    return dependency


def redirect_to_swagger_ui() -> RedirectResponse:
    return RedirectResponse(url="/docs")


def _register_exception_handlers(app: FastAPI) -> None:
    async def not_found_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        _ = request
        match exc:
            case NotFoundError() as not_found:
                error = ErrorResponse(detail=str(not_found))
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content=error.model_dump(),
                )
            case DomainValidationError() as invalid:
                error = ErrorResponse(detail=str(invalid))
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    content=error.model_dump(),
                )
            case ConfigurationError() as configuration_error:
                error = ErrorResponse(detail=str(configuration_error))
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content=error.model_dump(),
                )
            case UpstreamServiceError() as upstream_error:
                error = ErrorResponse(detail=str(upstream_error))
                return JSONResponse(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    content=error.model_dump(),
                )
            case _:
                raise exc

    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(DomainValidationError, not_found_handler)
    app.add_exception_handler(ConfigurationError, not_found_handler)
    app.add_exception_handler(UpstreamServiceError, not_found_handler)


app = create_app()
