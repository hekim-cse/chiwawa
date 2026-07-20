from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
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

MAX_OAUTH_STATES = 10_000


@dataclass(slots=True)
class AppState:
    trips: dict[str, TripRead] = field(default_factory=dict)
    photo_searches: dict[str, PhotoPlaceSearchResponse] = field(default_factory=dict)
    wanted_places: dict[str, WantedPlaceRead] = field(default_factory=dict)
    plan_jobs: dict[str, PlanJobRead] = field(default_factory=dict)
    plans: dict[str, PlanDraftRead] = field(default_factory=dict)
    schedule_items: dict[str, ScheduleItemRead] = field(default_factory=dict)
    recommendations: dict[str, FreeTimeRecommendationRead] = field(default_factory=dict)
    photos: dict[str, MemorialPhotoRead] = field(default_factory=dict)
    memorials: dict[str, MemorialRecordRead] = field(default_factory=dict)
    confirmed_plans: set[str] = field(default_factory=set)
    confirmed_plan_items: dict[str, list[str]] = field(default_factory=dict)
    replan_source_items: dict[str, list[str]] = field(default_factory=dict)
    confirmed_photo_places: dict[str, ConfirmedPhotoPlaceRead] = field(
        default_factory=dict,
    )
    added_recommendations: dict[str, str] = field(default_factory=dict)
    oauth_states: dict[str, datetime] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock, repr=False)

    def next_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex}"

    def issue_oauth_state(self, value: str, expires_at: datetime) -> None:
        with self.lock:
            self._purge_oauth_states(datetime.now(UTC))
            while len(self.oauth_states) >= MAX_OAUTH_STATES:
                oldest = next(iter(self.oauth_states))
                del self.oauth_states[oldest]
            self.oauth_states[value] = expires_at

    def consume_oauth_state(self, value: str, now: datetime) -> bool:
        with self.lock:
            self._purge_oauth_states(now)
            expires_at = self.oauth_states.pop(value, None)
            return expires_at is not None and expires_at > now

    def _purge_oauth_states(self, now: datetime) -> None:
        expired = [
            value
            for value, expires_at in self.oauth_states.items()
            if expires_at <= now
        ]
        for value in expired:
            del self.oauth_states[value]


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
