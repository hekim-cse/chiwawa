from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _db_path() -> Path:
    configured = os.getenv("GOOGLE_AUTH_DB_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[3] / "data" / "google_auth.db"


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[3] / "sql" / "001_google_users.sql"


def _ensure_schema(connection: sqlite3.Connection) -> None:
    schema_sql = _schema_path().read_text(encoding="utf-8")
    connection.executescript(schema_sql)
    connection.commit()


def _connect() -> sqlite3.Connection:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    _ensure_schema(connection)
    return connection


def save_or_update_user(user_data: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    google_sub = str(user_data["sub"])
    email = user_data.get("email")
    name = user_data.get("name")
    picture = user_data.get("picture")

    with _connect() as connection:
        existing = connection.execute(
            "SELECT created_at FROM google_users WHERE google_sub = ?",
            (google_sub,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now

        connection.execute(
            """
            INSERT INTO google_users (
                google_sub,
                email,
                name,
                picture,
                created_at,
                last_login_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(google_sub) DO UPDATE SET
                email = excluded.email,
                name = excluded.name,
                picture = excluded.picture,
                last_login_at = excluded.last_login_at
            """,
            (google_sub, email, name, picture, created_at, now),
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT id, google_sub, email, name, picture, created_at, last_login_at
            FROM google_users
            WHERE google_sub = ?
            """,
            (google_sub,),
        ).fetchone()

    return dict(row) if row else {}
