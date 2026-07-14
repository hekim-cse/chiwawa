from __future__ import annotations

import sqlite3
from importlib.resources import files
from typing import TYPE_CHECKING

from chiwawa_backend.config import Settings, get_settings
from chiwawa_backend.errors import ConfigurationError

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable
    from pathlib import Path

AUTH_DB_FILE_ERROR = "GOOGLE_AUTH_DB_PATH must point to a regular file"


def db_path(settings: Settings | None = None) -> Path:
    active_settings = settings or get_settings()
    return active_settings.auth_db_path()


def _sql_dir() -> Traversable:
    return files("chiwawa_backend").joinpath("sql")


def _ensure_schema(connection: sqlite3.Connection) -> None:
    scripts = sorted(
        (
            resource
            for resource in _sql_dir().iterdir()
            if resource.name.endswith(".sql")
        ),
        key=lambda resource: resource.name,
    )
    for script in scripts:
        _ = connection.executescript(script.read_text(encoding="utf-8"))
    _ = connection.execute("PRAGMA foreign_keys = ON")
    connection.commit()


def connect(settings: Settings | None = None) -> sqlite3.Connection:
    path = db_path(settings)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ConfigurationError(AUTH_DB_FILE_ERROR)
    if not path.exists():
        _ = path.touch(mode=0o600)
    path.chmod(0o600)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        _ensure_schema(connection)
    except (OSError, sqlite3.Error):
        connection.close()
        raise
    return connection
