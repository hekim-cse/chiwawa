from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class TravelStyle(StrEnum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    PACKED = "packed"


class PlaceSource(StrEnum):
    MANUAL = "manual"
    PHOTO = "photo"
    RECOMMENDATION = "recommendation"
    PLAN = "plan"


class PlanJobStatus(StrEnum):
    COMPLETED = "completed"


class HealthResponse(ApiModel):
    status: str
    service: str
    version: str


class ErrorResponse(ApiModel):
    detail: str
