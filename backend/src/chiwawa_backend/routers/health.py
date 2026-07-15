from fastapi import APIRouter, status

from chiwawa_backend import __version__
from chiwawa_backend.dependencies import SettingsDep, StartupRecoveryDep
from chiwawa_backend.routers.responses import error_responses
from chiwawa_backend.schemas.base import HealthResponse
from chiwawa_backend.services.readiness import check_readiness

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="chiwawa-backend", version=__version__)


@router.get(
    "/ready",
    responses=error_responses(status.HTTP_503_SERVICE_UNAVAILABLE),
)
def readiness_check(
    settings: SettingsDep,
    startup_recovery: StartupRecoveryDep,
) -> HealthResponse:
    check_readiness(settings, startup_recovery)
    return HealthResponse(
        status="ready",
        service="chiwawa-backend",
        version=__version__,
    )
