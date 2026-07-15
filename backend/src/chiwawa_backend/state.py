from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from threading import RLock
from typing import Concatenate
from uuid import uuid4

from chiwawa_backend.schemas.memorial import MemorialPhotoRead, MemorialRecordRead
from chiwawa_backend.schemas.places import (
    ConfirmedPhotoPlaceRead,
    PhotoPlaceSearchResponse,
    WantedPlaceRead,
)
from chiwawa_backend.schemas.plans import PlanDraftRead, PlanJobRead
from chiwawa_backend.schemas.schedule import ScheduleItemRead
from chiwawa_backend.schemas.travel import FreeTimeRecommendationRead
from chiwawa_backend.schemas.trips import TripRead


@dataclass(slots=True)  # noqa: RUF100  # noqa: MUTABLE_OK
class AppState:
    """Mutable request-local aggregate updated by synchronous domain services."""

    trips: dict[str, TripRead] = field(default_factory=dict)
    trip_owners: dict[str, int] = field(default_factory=dict)
    photo_searches: dict[str, PhotoPlaceSearchResponse] = field(default_factory=dict)
    wanted_places: dict[str, WantedPlaceRead] = field(default_factory=dict)
    plan_jobs: dict[str, PlanJobRead] = field(default_factory=dict)
    plans: dict[str, PlanDraftRead] = field(default_factory=dict)
    schedule_items: dict[str, ScheduleItemRead] = field(default_factory=dict)
    recommendations: dict[str, FreeTimeRecommendationRead] = field(default_factory=dict)
    photos: dict[str, MemorialPhotoRead] = field(default_factory=dict)
    memorials: dict[str, MemorialRecordRead] = field(default_factory=dict)
    confirmed_plans: set[str] = field(default_factory=set)
    confirmed_photo_places: dict[str, ConfirmedPhotoPlaceRead] = field(
        default_factory=dict,
    )
    added_recommendations: dict[str, str] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock, repr=False)

    def next_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex}"


def synchronized[**P, R](
    function: Callable[Concatenate[AppState, P], R],
) -> Callable[Concatenate[AppState, P], R]:
    @wraps(function)
    def locked(
        state: AppState,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        with state.lock:
            return function(state, *args, **kwargs)

    return locked
