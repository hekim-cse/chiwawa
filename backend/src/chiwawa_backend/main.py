from collections.abc import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from chiwawa_backend.config import load_env_file
from chiwawa_backend.dependencies import get_state
from chiwawa_backend.errors import NotFoundError
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
from chiwawa_backend.state import AppState


def create_app(state: AppState | None = None) -> FastAPI:
    load_env_file()
    app_state = state or AppState()
    app = FastAPI(
        title="Chiwawa Backend",
        description="AI 기반 일본 자유여행 일정 추천 및 관리 API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_api_route(
        "/",
        redirect_to_swagger_ui,
        methods=["GET"],
        include_in_schema=False,
    )
    app.dependency_overrides[get_state] = _state_dependency(app_state)
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
    ):
        app.include_router(router)
    return app


def _state_dependency(state: AppState) -> Callable[[], AppState]:
    def dependency() -> AppState:
        return state

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
            case _:
                raise exc

    app.add_exception_handler(NotFoundError, not_found_handler)


app = create_app()
