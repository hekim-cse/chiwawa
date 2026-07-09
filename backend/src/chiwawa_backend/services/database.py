from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def db_path() -> Path:
    configured = os.getenv("GOOGLE_AUTH_DB_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[3] / "data" / "google_auth.db"


def _sql_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "sql"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    _ = connection.execute("PRAGMA foreign_keys = ON")
    for script in sorted(_sql_dir().glob("*.sql")):
        _ = connection.executescript(script.read_text(encoding="utf-8"))
    connection.commit()
    return connection
