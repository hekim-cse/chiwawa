import contextlib
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar, Final, Literal, Protocol, Self, override

from pydantic import BaseModel, ConfigDict

from chiwawa_backend.config import Settings
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
from chiwawa_backend.services.database import connect
from chiwawa_backend.state import AppState

STATE_SCHEMA_VERSION: Final = 1


@dataclass(frozen=True, slots=True)
class StateSchemaVersionError(RuntimeError):
    found: int

    @override
    def __str__(self) -> str:
        return f"unsupported application state schema version: {self.found}"


class StateSnapshot(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = STATE_SCHEMA_VERSION
    trips: dict[str, TripRead]
    trip_owners: dict[str, int]
    photo_searches: dict[str, PhotoPlaceSearchResponse]
    wanted_places: dict[str, WantedPlaceRead]
    plan_jobs: dict[str, PlanJobRead]
    plans: dict[str, PlanDraftRead]
    schedule_items: dict[str, ScheduleItemRead]
    recommendations: dict[str, FreeTimeRecommendationRead]
    photos: dict[str, MemorialPhotoRead]
    memorials: dict[str, MemorialRecordRead]
    confirmed_plans: set[str]
    confirmed_photo_places: dict[str, ConfirmedPhotoPlaceRead]
    added_recommendations: dict[str, str]

    @classmethod
    def from_state(cls, state: AppState) -> Self:
        with state.lock:
            return cls(
                trips=dict(state.trips),
                trip_owners=dict(state.trip_owners),
                photo_searches=dict(state.photo_searches),
                wanted_places=dict(state.wanted_places),
                plan_jobs=dict(state.plan_jobs),
                plans=dict(state.plans),
                schedule_items=dict(state.schedule_items),
                recommendations=dict(state.recommendations),
                photos=dict(state.photos),
                memorials=dict(state.memorials),
                confirmed_plans=set(state.confirmed_plans),
                confirmed_photo_places=dict(state.confirmed_photo_places),
                added_recommendations=dict(state.added_recommendations),
            )

    def to_state(self) -> AppState:
        return AppState(
            trips=dict(self.trips),
            trip_owners=dict(self.trip_owners),
            photo_searches=dict(self.photo_searches),
            wanted_places=dict(self.wanted_places),
            plan_jobs=dict(self.plan_jobs),
            plans=dict(self.plans),
            schedule_items=dict(self.schedule_items),
            recommendations=dict(self.recommendations),
            photos=dict(self.photos),
            memorials=dict(self.memorials),
            confirmed_plans=set(self.confirmed_plans),
            confirmed_photo_places=dict(self.confirmed_photo_places),
            added_recommendations=dict(self.added_recommendations),
        )


class _SnapshotCursor(Protocol):
    def fetchone(self) -> tuple[int, str] | None: ...


@dataclass(frozen=True, slots=True)
class SQLiteStateStore:
    settings: Settings

    @contextmanager
    def transaction(self) -> Generator[AppState]:
        with contextlib.closing(connect(self.settings)) as connection, connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            state = self._load(
                connection.execute(
                    """
                SELECT schema_version, snapshot_json
                FROM app_state WHERE singleton_id = 1
                """
                )
            )
            yield state
            snapshot = StateSnapshot.from_state(state)
            _ = connection.execute(
                """
                INSERT INTO app_state (
                    singleton_id, schema_version, snapshot_json, updated_at
                ) VALUES (1, ?, ?, ?)
                ON CONFLICT(singleton_id) DO UPDATE SET
                    schema_version = excluded.schema_version,
                    snapshot_json = excluded.snapshot_json,
                    updated_at = excluded.updated_at
                """,
                (
                    snapshot.schema_version,
                    snapshot.model_dump_json(),
                    datetime.now(UTC).isoformat(),
                ),
            )

    @staticmethod
    def _load(cursor: _SnapshotCursor) -> AppState:
        row = cursor.fetchone()
        if row is None:
            return AppState()
        schema_version, snapshot_json = row
        if schema_version != STATE_SCHEMA_VERSION:
            raise StateSchemaVersionError(found=schema_version)
        return StateSnapshot.model_validate_json(snapshot_json).to_state()
