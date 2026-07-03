from dataclasses import dataclass, field

from chiwawa_backend.schemas.memorial import MemorialPhotoRead, MemorialRecordRead
from chiwawa_backend.schemas.places import (
    PhotoPlaceSearchResponse,
    WantedPlaceRead,
)
from chiwawa_backend.schemas.plans import PlanDraftRead, PlanJobRead
from chiwawa_backend.schemas.schedule import ScheduleItemRead
from chiwawa_backend.schemas.travel import FreeTimeRecommendationRead
from chiwawa_backend.schemas.trips import TripRead


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
    counters: dict[str, int] = field(default_factory=dict)

    def next_id(self, prefix: str) -> str:
        current = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = current
        return f"{prefix}_{current}"
