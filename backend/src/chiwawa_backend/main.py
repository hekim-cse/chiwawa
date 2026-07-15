import sys
from collections.abc import AsyncIterator, Callable
from contextlib import (
    AbstractContextManager,
)

from anyio import CancelScope, CapacityLimiter
from anyio.to_thread import run_sync
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from chiwawa_backend.config import Settings, get_settings
from chiwawa_backend.dependencies import (
    get_app_settings,
    get_oauth_state_store,
    get_startup_recovery_status,
    get_transaction_state,
)
from chiwawa_backend.exception_handlers import register_exception_handlers
from chiwawa_backend.middleware import (
    EarlyUploadAuthMiddleware,
    RequestBodyLimitMiddleware,
    SecurityHeadersMiddleware,
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
from chiwawa_backend.routers.responses import error_responses
from chiwawa_backend.services.oauth_state_store import OAuthStateStore
from chiwawa_backend.services.readiness import StartupRecoveryStatus
from chiwawa_backend.services.startup_recovery import create_application_lifespan
from chiwawa_backend.services.state_store import SQLiteStateStore
from chiwawa_backend.state import AppState


def create_app(
    state: AppState | None = None,
    settings: Settings | None = None,
    oauth_state_store: OAuthStateStore | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    startup_recovery = StartupRecoveryStatus()
    app = FastAPI(
        title="Chiwawa Backend",
        description="AI 기반 일본 자유여행 일정 추천 및 관리 API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        responses=error_responses(400, 413, 500),
        lifespan=create_application_lifespan(active_settings, startup_recovery),
    )
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_json_body_bytes=active_settings.max_json_body_bytes,
        max_multipart_body_bytes=active_settings.max_multipart_body_bytes,
    )
    app.add_middleware(EarlyUploadAuthMiddleware, settings=active_settings)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_api_route(
        "/",
        redirect_to_swagger_ui,
        methods=["GET"],
        include_in_schema=False,
    )
    app.dependency_overrides[get_transaction_state] = _select_state_dependency(
        state,
        active_settings,
    )
    app.dependency_overrides[get_oauth_state_store] = _value_dependency(
        oauth_state_store or OAuthStateStore(active_settings),
    )
    app.dependency_overrides[get_app_settings] = _value_dependency(active_settings)
    app.dependency_overrides[get_startup_recovery_status] = _value_dependency(
        startup_recovery,
    )
    register_exception_handlers(app)
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


def _select_state_dependency(
    state: AppState | None,
    settings: Settings,
) -> Callable[[], AppState] | Callable[[], AsyncIterator[AppState]]:
    if state is not None or not settings.is_production:
        return _value_dependency(state or AppState())
    return _persistent_state_dependency(SQLiteStateStore(settings))


def _persistent_state_dependency(
    store: SQLiteStateStore,
) -> Callable[[], AsyncIterator[AppState]]:
    gate = CapacityLimiter(1)
    transaction_threads = CapacityLimiter(1)

    async def dependency() -> AsyncIterator[AppState]:
        async with gate:
            transaction = store.transaction()
            state = await _enter_state_transaction(transaction, transaction_threads)
            try:
                yield state
            finally:
                exception_type, exception, traceback = sys.exc_info()
                with CancelScope(shield=True):
                    _ = await run_sync(
                        transaction.__exit__,
                        exception_type,
                        exception,
                        traceback,
                        limiter=transaction_threads,
                    )

    return dependency


async def _enter_state_transaction(
    transaction: AbstractContextManager[AppState],
    limiter: CapacityLimiter,
) -> AppState:
    with CancelScope(shield=True):
        return await run_sync(transaction.__enter__, limiter=limiter)
    message = "state transaction enter was cancelled"
    raise RuntimeError(message)


def _value_dependency[T](value: T) -> Callable[[], T]:
    def dependency() -> T:
        return value

    return dependency


def redirect_to_swagger_ui() -> RedirectResponse:
    return RedirectResponse(url="/docs")


app = create_app()
