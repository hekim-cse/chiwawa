from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final, Protocol, override

from chiwawa_backend.services.database import connect

if TYPE_CHECKING:
    from chiwawa_backend.config import Settings

DEFAULT_OAUTH_STATE_CAPACITY: Final = 10_000


@dataclass(frozen=True, slots=True)
class OAuthStateCapacityError(RuntimeError):
    capacity: int

    @override
    def __str__(self) -> str:
        return f"OAuth state capacity reached: {self.capacity}"


@dataclass(frozen=True, slots=True)
class OAuthStateConfigurationError(ValueError):
    capacity: int

    @override
    def __str__(self) -> str:
        return f"OAuth state capacity must be positive: {self.capacity}"


@dataclass(frozen=True, slots=True)
class OAuthStateTimeError(ValueError):
    @override
    def __str__(self) -> str:
        return "OAuth state timestamps must include a UTC offset"


@dataclass(frozen=True, slots=True)
class OAuthStateCollisionError(ValueError):
    value: str

    @override
    def __str__(self) -> str:
        return "OAuth state value already exists"


class _CountCursor(Protocol):
    def fetchone(self) -> tuple[int]: ...


class _ValueCursor(Protocol):
    def fetchone(self) -> tuple[str] | None: ...


@dataclass(frozen=True, slots=True)
class OAuthStateStore:
    settings: Settings
    capacity: int = DEFAULT_OAUTH_STATE_CAPACITY

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise OAuthStateConfigurationError(capacity=self.capacity)

    def issue(self, value: str, expires_at: datetime) -> None:
        issued_at = datetime.now(UTC)
        with contextlib.closing(connect(self.settings)) as connection, connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            _ = connection.execute(
                "DELETE FROM oauth_states WHERE expires_at <= ?",
                (_utc_text(issued_at),),
            )
            existing = _fetch_value(
                connection.execute(
                    "SELECT value FROM oauth_states WHERE value = ?",
                    (value,),
                )
            )
            count = _fetch_count(
                connection.execute("SELECT COUNT(*) FROM oauth_states")
            )
            if existing is not None:
                raise OAuthStateCollisionError(value=value)
            if count >= self.capacity:
                raise OAuthStateCapacityError(capacity=self.capacity)
            _ = connection.execute(
                """
                INSERT INTO oauth_states (value, expires_at, issued_at)
                VALUES (?, ?, ?)
                """,
                (value, _utc_text(expires_at), _utc_text(issued_at)),
            )

    def consume(self, value: str, now: datetime) -> bool:
        with contextlib.closing(connect(self.settings)) as connection, connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            _ = connection.execute(
                "DELETE FROM oauth_states WHERE expires_at <= ?",
                (_utc_text(now),),
            )
            consumed = _fetch_value(
                connection.execute(
                    "DELETE FROM oauth_states WHERE value = ? RETURNING value",
                    (value,),
                )
            )
            return consumed is not None

    def purge(self, now: datetime) -> int:
        with contextlib.closing(connect(self.settings)) as connection, connection:
            _ = connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "DELETE FROM oauth_states WHERE expires_at <= ?",
                (_utc_text(now),),
            )
            return cursor.rowcount


def _fetch_count(cursor: _CountCursor) -> int:
    return cursor.fetchone()[0]


def _fetch_value(cursor: _ValueCursor) -> str | None:
    row = cursor.fetchone()
    return None if row is None else row[0]


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise OAuthStateTimeError
    return value.astimezone(UTC).isoformat(timespec="microseconds")
