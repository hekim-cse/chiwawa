from __future__ import annotations

import contextlib
import sqlite3
import time
from dataclasses import dataclass
from importlib.resources import files
from threading import RLock
from typing import TYPE_CHECKING, Final, Protocol

from chiwawa_backend.config import Settings, get_settings
from chiwawa_backend.errors import ConfigurationError

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable
    from pathlib import Path

AUTH_DB_FILE_ERROR: Final = "DATABASE_PATH must point to a regular file"
WAL_MODE_ERROR: Final = "SQLite WAL mode is required"
SQLITE_LOCK_ERRORS: Final = frozenset((sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED))
WAL_RETRY_INTERVAL_SECONDS: Final = 0.01
MIGRATION_LEDGER_SQL: Final = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""
_INITIALIZATION_LOCK: Final = RLock()
_INITIALIZED_DATABASES: dict[Path, tuple[int, int]] = {}


class DatabasePathUnavailableError(ConfigurationError):
    pass


@dataclass(frozen=True, slots=True)
class _Migration:
    version: int
    name: str
    sql: str


class _TextScalarCursor(Protocol):
    def fetchone(self) -> tuple[str] | None: ...


class _IntScalarCursor(Protocol):
    def fetchone(self) -> tuple[int] | None: ...


def _fetch_text(cursor: _TextScalarCursor) -> str | None:
    row = cursor.fetchone()
    return None if row is None else row[0]


def _fetch_int(cursor: _IntScalarCursor) -> int | None:
    row = cursor.fetchone()
    return None if row is None else row[0]


def db_path(settings: Settings | None = None) -> Path:
    active_settings = settings or get_settings()
    return active_settings.auth_db_path()


def _sql_dir() -> Traversable:
    return files("chiwawa_backend").joinpath("sql")


def _migrations() -> list[_Migration]:
    migrations: list[_Migration] = []
    versions: set[int] = set()
    for resource in _sql_dir().iterdir():
        version_text, separator, _description = resource.name.partition("_")
        if resource.name.endswith(".sql") and separator and version_text.isdecimal():
            version = int(version_text)
            if version in versions:
                message = f"Duplicate migration version {version}"
                raise ConfigurationError(message)
            versions.add(version)
            migrations.append(
                _Migration(
                    version=version,
                    name=resource.name,
                    sql=resource.read_text(encoding="utf-8"),
                ),
            )
    return sorted(migrations, key=lambda migration: migration.version)


def _prepare_database_file(settings: Settings) -> Path:
    path = settings.auth_db_path()
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise DatabasePathUnavailableError(AUTH_DB_FILE_ERROR)
        if not path.exists():
            _ = path.touch(mode=0o600)
        path.chmod(0o600)
    except OSError as error:
        raise DatabasePathUnavailableError(AUTH_DB_FILE_ERROR) from error
    return path


def _open_connection(settings: Settings) -> sqlite3.Connection:
    connection = sqlite3.connect(
        _prepare_database_file(settings),
        timeout=settings.sqlite_busy_timeout_ms / 1000,
        check_same_thread=False,
    )
    with contextlib.ExitStack() as cleanup:
        _ = cleanup.callback(connection.close)
        _ = connection.execute(
            f"PRAGMA busy_timeout = {settings.sqlite_busy_timeout_ms}",
        )
        _ = connection.execute("PRAGMA foreign_keys = ON")
        _enable_wal(connection, settings.sqlite_busy_timeout_ms)
        connection.row_factory = sqlite3.Row
        _ = cleanup.pop_all()
    return connection


def _enable_wal(connection: sqlite3.Connection, busy_timeout_ms: int) -> None:
    deadline = time.monotonic() + (busy_timeout_ms / 1000)
    while True:
        try:
            result = _fetch_text(connection.execute("PRAGMA journal_mode = WAL"))
        except sqlite3.OperationalError as error:
            if (
                error.sqlite_errorcode not in SQLITE_LOCK_ERRORS
                or time.monotonic() >= deadline
            ):
                raise
            time.sleep(WAL_RETRY_INTERVAL_SECONDS)
            continue
        if result != "wal":
            raise ConfigurationError(WAL_MODE_ERROR)
        return


def _execute_script(connection: sqlite3.Connection, script: str) -> None:
    statement = ""
    for line in script.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            if statement.strip():
                _ = connection.execute(statement)
            statement = ""
    if statement.strip():
        _ = connection.execute(statement)


def _ensure_migration_ledger(connection: sqlite3.Connection) -> None:
    with connection:
        _ = connection.execute("BEGIN IMMEDIATE")
        _ = connection.execute(MIGRATION_LEDGER_SQL)


def _apply_migration(
    connection: sqlite3.Connection,
    migration: _Migration,
) -> None:
    with connection:
        _ = connection.execute("BEGIN IMMEDIATE")
        existing_name = _fetch_text(
            connection.execute(
                "SELECT name FROM schema_migrations WHERE version = ?",
                (migration.version,),
            ),
        )
        if existing_name is not None:
            if existing_name != migration.name:
                message = (
                    f"Migration ledger mismatch for version {migration.version}: "
                    f"expected {migration.name}, found {existing_name}"
                )
                raise ConfigurationError(message)
            return
        _execute_script(connection, migration.sql)
        _ = connection.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
            (migration.version, migration.name),
        )


def _database_identity(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return stat.st_dev, stat.st_ino


def _remember_initialization(settings: Settings) -> None:
    path = settings.auth_db_path()
    identity = _database_identity(path)
    if identity is not None:
        with _INITIALIZATION_LOCK:
            _INITIALIZED_DATABASES[path] = identity


def initialize_database(settings: Settings) -> None:
    migrations = _migrations()
    with contextlib.closing(_open_connection(settings)) as connection:
        _ensure_migration_ledger(connection)
        for migration in migrations:
            _apply_migration(connection, migration)
    _remember_initialization(settings)


def _initialize_for_connect(settings: Settings) -> None:
    path = settings.auth_db_path()
    with _INITIALIZATION_LOCK:
        identity = _database_identity(path)
        if identity is not None and _INITIALIZED_DATABASES.get(path) == identity:
            return
        initialize_database(settings)


def current_migration_version(settings: Settings) -> int:
    with contextlib.closing(_open_connection(settings)) as connection:
        connection.row_factory = None
        ledger_count = _fetch_int(
            connection.execute(
                """
                SELECT COUNT(*) FROM sqlite_master
                WHERE type = 'table' AND name = 'schema_migrations'
                """,
            ),
        )
        if ledger_count in (None, 0):
            return 0
        version = _fetch_int(
            connection.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations",
            ),
        )
        if version is not None:
            return version
    return 0


def latest_migration_version() -> int:
    migrations = _migrations()
    return 0 if not migrations else migrations[-1].version


def connect(settings: Settings | None = None) -> sqlite3.Connection:
    active_settings = settings or get_settings()
    _initialize_for_connect(active_settings)
    return _open_connection(active_settings)
