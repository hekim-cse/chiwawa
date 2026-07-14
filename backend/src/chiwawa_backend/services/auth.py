from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import Protocol

from chiwawa_backend.config import Settings, get_settings
from chiwawa_backend.schemas.auth import GoogleUserProfile, GoogleUserRead
from chiwawa_backend.services.database import connect

SELECT_CREATED_SQL = "SELECT created_at FROM google_users WHERE google_sub = ?"
UPSERT_USER_SQL = """
    INSERT INTO google_users (
        google_sub, email, name, picture, created_at, last_login_at
    ) VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(google_sub) DO UPDATE SET
        email = excluded.email,
        name = excluded.name,
        picture = excluded.picture,
        last_login_at = excluded.last_login_at
"""
SELECT_USER_SQL = """
    SELECT id, google_sub, email, name, picture, created_at, last_login_at
    FROM google_users
    WHERE google_sub = ?
"""
USER_COLUMN_COUNT = 7
USER_ROW_ERROR = "Google user upsert did not return a complete row"
DATABASE_TEXT_ERROR = "database value must be text"
DATABASE_OPTIONAL_TEXT_ERROR = "database value must be text or null"


class ObjectRowCursor(Protocol):
    def fetchone(self) -> tuple[object, ...] | None: ...


def _fetch_one(cursor: ObjectRowCursor) -> tuple[object, ...] | None:
    return cursor.fetchone()


def save_or_update_user(
    profile: GoogleUserProfile,
    settings: Settings | None = None,
) -> GoogleUserRead:
    active_settings = settings or get_settings()
    now = datetime.now(UTC).replace(microsecond=0).isoformat()

    with contextlib.closing(connect(active_settings)) as connection, connection:
        existing = _fetch_one(connection.execute(SELECT_CREATED_SQL, (profile.sub,)))
        created_at = _text(existing[0]) if existing is not None else now
        _ = connection.execute(
            UPSERT_USER_SQL,
            (
                profile.sub,
                profile.email,
                profile.name,
                profile.picture,
                created_at,
                now,
            ),
        )
        row = _fetch_one(connection.execute(SELECT_USER_SQL, (profile.sub,)))

    if row is None or len(row) != USER_COLUMN_COUNT:
        raise RuntimeError(USER_ROW_ERROR)
    user_id, google_sub, email, name, picture, created_at, last_login_at = row
    return GoogleUserRead(
        id=_text(user_id),
        google_sub=_text(google_sub),
        email=_optional_text(email),
        name=_optional_text(name),
        picture=_optional_text(picture),
        created_at=_datetime(created_at),
        last_login_at=_datetime(last_login_at),
    )


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    raise TypeError(DATABASE_TEXT_ERROR)


def _optional_text(value: object) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise TypeError(DATABASE_OPTIONAL_TEXT_ERROR)


def _datetime(value: object) -> datetime:
    return datetime.fromisoformat(_text(value))
