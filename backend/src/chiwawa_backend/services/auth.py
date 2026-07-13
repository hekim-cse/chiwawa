from __future__ import annotations

import sqlite3
from contextlib import suppress
from datetime import UTC, datetime
from importlib.resources import files
from typing import Protocol

from chiwawa_backend.config import Settings, get_settings
from chiwawa_backend.errors import ConfigurationError
from chiwawa_backend.schemas.auth import GoogleUserProfile, GoogleUserRead

SELECT_CREATED_SQL = "SELECT created_at FROM google_users WHERE google_sub = ?"
INSERT_PREFIX = "INSERT INTO google_users "
USER_COLUMNS = "(google_sub, email, name, picture, created_at, last_login_at) "
INSERT_VALUES = "VALUES (?, ?, ?, ?, ?, ?) "
CONFLICT_ACTION = "ON CONFLICT(google_sub) DO UPDATE SET "
IDENTITY_UPDATE = "email = excluded.email, name = excluded.name, "
PROFILE_UPDATE = "picture = excluded.picture, last_login_at = excluded.last_login_at"
UPSERT_USER_SQL = (
    INSERT_PREFIX
    + USER_COLUMNS
    + INSERT_VALUES
    + CONFLICT_ACTION
    + IDENTITY_UPDATE
    + PROFILE_UPDATE
)
SELECT_USER_COLUMNS = (
    "SELECT id, google_sub, email, name, picture, created_at, last_login_at "
)
SELECT_USER_FILTER = "FROM google_users WHERE google_sub = ?"
SELECT_USER_SQL = SELECT_USER_COLUMNS + SELECT_USER_FILTER
AUTH_DB_FILE_ERROR = "GOOGLE_AUTH_DB_PATH must point to a regular file"


class ObjectRowCursor(Protocol):
    def fetchone(self) -> tuple[object, ...] | None: ...


def _fetch_one(cursor: ObjectRowCursor) -> tuple[object, ...] | None:
    return cursor.fetchone()


def _ensure_schema(connection: sqlite3.Connection) -> None:
    schema_sql = (
        files("chiwawa_backend")
        .joinpath("sql", "001_google_users.sql")
        .read_text(encoding="utf-8")
    )
    _ = connection.executescript(schema_sql)
    connection.commit()


def _connect(settings: Settings) -> sqlite3.Connection:
    db_path = settings.auth_db_path()
    parent_exists = db_path.parent.exists()
    db_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not parent_exists:
        db_path.parent.chmod(0o700)
    with suppress(FileExistsError):
        db_path.touch(mode=0o600, exist_ok=False)
    if db_path.is_symlink() or not db_path.is_file():
        raise ConfigurationError(AUTH_DB_FILE_ERROR)
    db_path.chmod(0o600)
    connection = sqlite3.connect(db_path)
    _ensure_schema(connection)
    return connection


def save_or_update_user(
    profile: GoogleUserProfile,
    settings: Settings | None = None,
) -> GoogleUserRead:
    active_settings = settings or get_settings()
    now = datetime.now(UTC).replace(microsecond=0).isoformat()

    connection = _connect(active_settings)
    try:
        existing = _fetch_one(
            connection.execute(SELECT_CREATED_SQL, (profile.sub,)),
        )
        created_at = str(existing[0]) if existing is not None else now

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
        connection.commit()
        row = _fetch_one(connection.execute(SELECT_USER_SQL, (profile.sub,)))
    finally:
        connection.close()

    if row is None:
        msg = "Google user upsert did not return a row"
        raise RuntimeError(msg)
    return GoogleUserRead.model_validate(
        {
            "id": str(row[0]),
            "google_sub": row[1],
            "email": row[2],
            "name": row[3],
            "picture": row[4],
            "created_at": row[5],
            "last_login_at": row[6],
        },
    )
