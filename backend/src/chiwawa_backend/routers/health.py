from fastapi import APIRouter

from chiwawa_backend import __version__
from chiwawa_backend.schemas.base import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="chiwawa-backend", version=__version__)
