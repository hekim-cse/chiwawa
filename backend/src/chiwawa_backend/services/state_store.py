# 여행·등록 장소·확정 일정 상태를 SQLite에 영속화하는 저장소
from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

from pydantic import BaseModel

from chiwawa_backend.errors import ConfigurationError
from chiwawa_backend.schemas.places import WantedPlaceRead
from chiwawa_backend.schemas.plans import ConfirmedRouteOptimizationRead
from chiwawa_backend.schemas.schedule import ScheduleItemRead
from chiwawa_backend.schemas.trips import TripRead

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from chiwawa_backend.config import Settings

APP_DB_FILE_ERROR = "APP_DB_PATH는 일반 파일을 가리켜야 합니다."


@dataclass(frozen=True, slots=True)
class PersistedState:
    trips: dict[str, TripRead]
    wanted_places: dict[str, WantedPlaceRead]
    schedule_items: dict[str, ScheduleItemRead]
    confirmed_route_items: dict[tuple[str, int], list[str]]
    confirmed_routes: dict[tuple[str, int], ConfirmedRouteOptimizationRead]


class StateStore(Protocol):
    def load(self) -> PersistedState: ...

    def save(
        self,
        *,
        trips: Mapping[str, TripRead],
        wanted_places: Mapping[str, WantedPlaceRead],
        schedule_items: Mapping[str, ScheduleItemRead],
        confirmed_route_items: Mapping[tuple[str, int], list[str]],
        confirmed_routes: Mapping[tuple[str, int], ConfirmedRouteOptimizationRead],
    ) -> None: ...


class SQLiteStateStore:
    """서비스 상태를 하나의 SQLite 트랜잭션으로 저장한다."""

    def __init__(self, path: Path) -> None:
        self._path: Path = path.expanduser().resolve()
        self._last_serialized: tuple[object, ...] | None = None
        self._prepare_file()
        with closing(self._connect()) as connection:
            self._ensure_schema(connection)

    @classmethod
    def from_settings(cls, settings: Settings) -> SQLiteStateStore:
        return cls(settings.application_db_path())

    def load(self) -> PersistedState:
        with closing(self._connect()) as connection:
            trips = self._load_models(connection, "trips", TripRead)
            wanted_places = self._load_models(
                connection,
                "wanted_places",
                WantedPlaceRead,
            )
            schedule_items = self._load_models(
                connection,
                "schedule_items",
                ScheduleItemRead,
            )
            route_rows = cast(
                "list[sqlite3.Row]",
                connection.execute(
                    """
                SELECT trip_id, day_index, schedule_item_id
                FROM confirmed_route_items
                ORDER BY trip_id, day_index, item_order
                """,
                ).fetchall(),
            )
            confirmed_routes = self._load_confirmed_routes(connection)
        confirmed_route_items: dict[tuple[str, int], list[str]] = {}
        for row in route_rows:
            key = (
                cast("str", row["trip_id"]),
                cast("int", row["day_index"]),
            )
            confirmed_route_items.setdefault(key, []).append(
                cast("str", row["schedule_item_id"]),
            )
        persisted = PersistedState(
            trips=trips,
            wanted_places=wanted_places,
            schedule_items=schedule_items,
            confirmed_route_items=confirmed_route_items,
            confirmed_routes=confirmed_routes,
        )
        self._last_serialized = self._serialize(
            trips,
            wanted_places,
            schedule_items,
            confirmed_route_items,
            confirmed_routes,
        )
        return persisted

    def save(
        self,
        *,
        trips: Mapping[str, TripRead],
        wanted_places: Mapping[str, WantedPlaceRead],
        schedule_items: Mapping[str, ScheduleItemRead],
        confirmed_route_items: Mapping[tuple[str, int], list[str]],
        confirmed_routes: Mapping[tuple[str, int], ConfirmedRouteOptimizationRead],
    ) -> None:
        serialized = self._serialize(
            trips,
            wanted_places,
            schedule_items,
            confirmed_route_items,
            confirmed_routes,
        )
        if serialized == self._last_serialized:
            return
        with closing(self._connect()) as connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            try:
                _ = connection.execute("DELETE FROM confirmed_route_items")
                _ = connection.execute("DELETE FROM confirmed_routes")
                _ = connection.execute("DELETE FROM schedule_items")
                _ = connection.execute("DELETE FROM wanted_places")
                _ = connection.execute("DELETE FROM trips")
                self._insert_trips(connection, trips)
                self._insert_trip_children(
                    connection,
                    "wanted_places",
                    wanted_places,
                )
                self._insert_trip_children(
                    connection,
                    "schedule_items",
                    schedule_items,
                )
                _ = connection.executemany(
                    """
                    INSERT INTO confirmed_route_items(
                        trip_id, day_index, item_order, schedule_item_id
                    ) VALUES (?, ?, ?, ?)
                    """,
                    [
                        (trip_id, day_index, item_order, item_id)
                        for (
                            trip_id,
                            day_index,
                        ), item_ids in confirmed_route_items.items()
                        for item_order, item_id in enumerate(item_ids)
                    ],
                )
                _ = connection.executemany(
                    """
                    INSERT INTO confirmed_routes(trip_id, day_index, payload_json)
                    VALUES (?, ?, ?)
                    """,
                    [
                        (trip_id, day_index, route.model_dump_json())
                        for (trip_id, day_index), route in confirmed_routes.items()
                    ],
                )
                connection.commit()
                self._last_serialized = serialized
            except Exception:
                connection.rollback()
                raise

    def _prepare_file(self) -> None:
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self._path.is_symlink() or (
            self._path.exists() and not self._path.is_file()
        ):
            raise ConfigurationError(APP_DB_FILE_ERROR)
        if not self._path.exists():
            _ = self._path.touch(mode=0o600)
        self._path.chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        _ = connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        _ = connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS trips (
                id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS wanted_places (
                id TEXT PRIMARY KEY,
                trip_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_wanted_places_trip_id
                ON wanted_places(trip_id);
            CREATE TABLE IF NOT EXISTS schedule_items (
                id TEXT PRIMARY KEY,
                trip_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_schedule_items_trip_id
                ON schedule_items(trip_id);
            CREATE TABLE IF NOT EXISTS confirmed_route_items (
                trip_id TEXT NOT NULL,
                day_index INTEGER NOT NULL CHECK(day_index > 0),
                item_order INTEGER NOT NULL CHECK(item_order >= 0),
                schedule_item_id TEXT NOT NULL,
                PRIMARY KEY (trip_id, day_index, item_order),
                UNIQUE (schedule_item_id),
                FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
                FOREIGN KEY (schedule_item_id) REFERENCES schedule_items(id)
                    ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS confirmed_routes (
                trip_id TEXT NOT NULL,
                day_index INTEGER NOT NULL CHECK(day_index > 0),
                payload_json TEXT NOT NULL,
                PRIMARY KEY (trip_id, day_index),
                FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
            );
            """,
        )
        connection.commit()

    @staticmethod
    def _load_models[ModelT: BaseModel](
        connection: sqlite3.Connection,
        table: str,
        model_type: type[ModelT],
    ) -> dict[str, ModelT]:
        rows = cast(
            "list[sqlite3.Row]",
            connection.execute(
                f"SELECT id, payload_json FROM {table} ORDER BY rowid",  # noqa: S608
            ).fetchall(),
        )
        return {
            cast("str", row["id"]): model_type.model_validate_json(
                cast("str", row["payload_json"]),
            )
            for row in rows
        }

    @staticmethod
    def _insert_trips(
        connection: sqlite3.Connection,
        items: Mapping[str, TripRead],
    ) -> None:
        _ = connection.executemany(
            "INSERT INTO trips(id, payload_json) VALUES (?, ?)",
            [(item_id, item.model_dump_json()) for item_id, item in items.items()],
        )

    @staticmethod
    def _load_confirmed_routes(
        connection: sqlite3.Connection,
    ) -> dict[tuple[str, int], ConfirmedRouteOptimizationRead]:
        rows = cast(
            "list[sqlite3.Row]",
            connection.execute(
                """
                SELECT trip_id, day_index, payload_json
                FROM confirmed_routes
                ORDER BY trip_id, day_index
                """,
            ).fetchall(),
        )
        return {
            (
                cast("str", row["trip_id"]),
                cast("int", row["day_index"]),
            ): ConfirmedRouteOptimizationRead.model_validate_json(
                cast("str", row["payload_json"]),
            )
            for row in rows
        }

    @staticmethod
    def _insert_trip_children(
        connection: sqlite3.Connection,
        table: str,
        items: Mapping[str, WantedPlaceRead] | Mapping[str, ScheduleItemRead],
    ) -> None:
        _ = connection.executemany(
            f"INSERT INTO {table}(id, trip_id, payload_json) VALUES (?, ?, ?)",  # noqa: S608
            [
                (item_id, item.trip_id, item.model_dump_json())
                for item_id, item in items.items()
            ],
        )

    @staticmethod
    def _serialize(
        trips: Mapping[str, TripRead],
        wanted_places: Mapping[str, WantedPlaceRead],
        schedule_items: Mapping[str, ScheduleItemRead],
        confirmed_route_items: Mapping[tuple[str, int], list[str]],
        confirmed_routes: Mapping[tuple[str, int], ConfirmedRouteOptimizationRead],
    ) -> tuple[object, ...]:
        return (
            tuple((key, value.model_dump_json()) for key, value in trips.items()),
            tuple(
                (key, value.model_dump_json()) for key, value in wanted_places.items()
            ),
            tuple(
                (key, value.model_dump_json()) for key, value in schedule_items.items()
            ),
            tuple((key, tuple(value)) for key, value in confirmed_route_items.items()),
            tuple(
                (key, value.model_dump_json())
                for key, value in confirmed_routes.items()
            ),
        )
