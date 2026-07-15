from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Final, cast

from chiwawa_backend.errors import (
    ApplicationError,
    ConfigurationError,
    InsufficientStorageError,
)

if TYPE_CHECKING:
    import sqlite3

    from chiwawa_backend.services.local_photo_store import LocalPhotoStore

RATE_WINDOW: Final = dt.timedelta(hours=1)
PAIR_SIZE: Final = 2


def purge(connection: sqlite3.Connection, now: dt.datetime) -> None:
    _ = connection.execute(
        "DELETE FROM upload_leases WHERE expires_at <= ?",
        (now.isoformat(),),
    )
    _ = connection.execute(
        "DELETE FROM upload_events WHERE created_at <= ?",
        ((now - RATE_WINDOW).isoformat(),),
    )


def backfill_legacy_sizes(
    connection: sqlite3.Connection,
    store: LocalPhotoStore,
    user_id: int,
) -> ApplicationError | None:
    rows = cast(
        "list[sqlite3.Row]",
        connection.execute(
            """
            SELECT id, stored_path FROM memorial_photos
            WHERE user_id = ? AND size_bytes = 0
            """,
            (user_id,),
        ).fetchall(),
    )
    try:
        for row in rows:
            relative = store.normalize_user_stored_path(
                user_id,
                _row_text(row, "stored_path"),
            )
            size_bytes = store.resolve(relative).stat().st_size
            _ = connection.execute(
                """
                UPDATE memorial_photos SET stored_path = ?, size_bytes = ?
                WHERE id = ? AND user_id = ?
                """,
                (relative.as_posix(), size_bytes, _row_int(row, "id"), user_id),
            )
    except OSError:
        return InsufficientStorageError("photo storage integrity check failed")
    return None


def record_attempt(
    connection: sqlite3.Connection,
    user_id: int,
    size_bytes: int,
    now: dt.datetime,
) -> None:
    _ = connection.execute(
        """
        INSERT INTO upload_events (user_id, size_bytes, created_at)
        VALUES (?, ?, ?)
        """,
        (user_id, max(size_bytes, 0), now.isoformat()),
    )


def photo_usage(connection: sqlite3.Connection, user_id: int) -> tuple[int, int]:
    row = cast(
        "sqlite3.Row | None",
        connection.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(size_bytes), 0)
            FROM memorial_photos WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone(),
    )
    return _usage_pair(row)


def lease_usage(connection: sqlite3.Connection, user_id: int) -> tuple[int, int]:
    row = cast(
        "sqlite3.Row | None",
        connection.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(reserved_bytes), 0)
            FROM upload_leases WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone(),
    )
    return _usage_pair(row)


def rate_usage(connection: sqlite3.Connection, user_id: int) -> tuple[int, str]:
    row = cast(
        "sqlite3.Row | None",
        connection.execute(
            """
            SELECT COUNT(*), COALESCE(MAX(created_at), '')
            FROM upload_events WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone(),
    )
    count = None if row is None else _row_value(row, 0)
    newest = None if row is None else _row_value(row, 1)
    if not isinstance(count, int) or not isinstance(newest, str):
        message = "invalid upload event usage row"
        raise ConfigurationError(message)
    return count, newest


def global_lease_usage(connection: sqlite3.Connection) -> tuple[int, int]:
    row = cast(
        "sqlite3.Row | None",
        connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(reserved_bytes), 0) FROM upload_leases"
        ).fetchone(),
    )
    return _usage_pair(row)


def _usage_pair(row: sqlite3.Row | None) -> tuple[int, int]:
    first = None if row is None else _row_value(row, 0)
    second = None if row is None else _row_value(row, 1)
    if row is None or len(row) != PAIR_SIZE:
        message = "invalid upload usage row"
        raise ConfigurationError(message)
    if not isinstance(first, int) or not isinstance(second, int):
        message = "invalid upload usage row"
        raise ConfigurationError(message)
    return first, second


def _row_value(row: sqlite3.Row, key: str | int) -> str | int | float | None:
    return cast("str | int | float | None", row[key])


def _row_text(row: sqlite3.Row, key: str) -> str:
    value = _row_value(row, key)
    if not isinstance(value, str):
        message = f"invalid text column: {key}"
        raise ConfigurationError(message)
    return value


def _row_int(row: sqlite3.Row, key: str) -> int:
    value = _row_value(row, key)
    if not isinstance(value, int):
        message = f"invalid integer column: {key}"
        raise ConfigurationError(message)
    return value
