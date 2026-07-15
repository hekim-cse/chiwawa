from __future__ import annotations

import contextlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from importlib.resources import files
from typing import TYPE_CHECKING, Protocol

import pytest

from chiwawa_backend.config import Settings
from chiwawa_backend.errors import ConfigurationError
from chiwawa_backend.services import database

if TYPE_CHECKING:
    from pathlib import Path


class _MigrationRowsCursor(Protocol):
    def fetchall(self) -> list[tuple[int, str]]: ...


class _TextScalarCursor(Protocol):
    def fetchone(self) -> tuple[str] | None: ...


class _IntScalarCursor(Protocol):
    def fetchone(self) -> tuple[int] | None: ...


def _fetch_text(cursor: _TextScalarCursor) -> tuple[str] | None:
    return cursor.fetchone()


def _fetch_int(cursor: _IntScalarCursor) -> tuple[int] | None:
    return cursor.fetchone()


def _settings(db_path: Path) -> Settings:
    return Settings(google_auth_db_path=db_path)


def _migration_rows(db_path: Path) -> list[tuple[int, str]]:
    with contextlib.closing(sqlite3.connect(db_path)) as connection:
        cursor: _MigrationRowsCursor = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version",
        )
        return cursor.fetchall()


def test_migrations_are_recorded_once(tmp_path: Path) -> None:
    # Given: an empty database path.
    settings = _settings(tmp_path / "app.db")

    # When: database initialization runs twice.
    database.initialize_database(settings)
    database.initialize_database(settings)

    # Then: every packaged migration has exactly one ledger entry.
    assert _migration_rows(settings.auth_db_path()) == [
        (1, "001_google_users.sql"),
        (2, "002_memorial_photos.sql"),
        (3, "003_app_state.sql"),
        (4, "004_oauth_states.sql"),
        (5, "005_memorial_hardening.sql"),
        (6, "006_upload_request_slots.sql"),
    ]
    assert database.current_migration_version(settings) == 6


def test_failed_migration_is_not_recorded_or_partially_applied(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: a migrated database and a later script that fails after creating a table.
    settings = _settings(tmp_path / "app.db")
    database.initialize_database(settings)
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    _ = (migration_dir / "007_broken.sql").write_text(
        """CREATE TABLE partial_migration (id INTEGER);
INSERT INTO table_that_does_not_exist (id) VALUES (1);
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(database, "_sql_dir", lambda: migration_dir)

    # When: the broken migration is attempted.
    with pytest.raises(sqlite3.OperationalError):
        database.initialize_database(settings)

    # Then: neither its ledger row nor its earlier DDL is committed.
    assert database.current_migration_version(settings) == 6
    with contextlib.closing(sqlite3.connect(settings.auth_db_path())) as connection:
        table = _fetch_text(
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'partial_migration'",
            ),
        )
    assert table is None


def test_connections_enable_wal_foreign_keys_and_busy_timeout(tmp_path: Path) -> None:
    # Given: an initialized application database.
    settings = _settings(tmp_path / "app.db")

    # When: a service connection is opened.
    with contextlib.closing(database.connect(settings)) as connection:
        connection.row_factory = None
        journal_mode = _fetch_text(connection.execute("PRAGMA journal_mode"))
        foreign_keys = _fetch_int(connection.execute("PRAGMA foreign_keys"))
        busy_timeout = _fetch_int(connection.execute("PRAGMA busy_timeout"))

    # Then: multi-worker-safe SQLite connection settings are active.
    assert journal_mode == ("wal",)
    assert foreign_keys == (1,)
    assert busy_timeout == (5_000,)


def test_existing_legacy_database_is_upgraded_with_safe_backfill(
    tmp_path: Path,
) -> None:
    # Given: a database created by the old 001/002 script replay implementation.
    db_path = tmp_path / "legacy.db"
    with contextlib.closing(sqlite3.connect(db_path)) as connection:
        for name in ("001_google_users.sql", "002_memorial_photos.sql"):
            script = (
                files("chiwawa_backend")
                .joinpath("sql", name)
                .read_text(
                    encoding="utf-8",
                )
            )
            _ = connection.executescript(script)
        _ = connection.execute(
            """
            INSERT INTO google_users (
                google_sub, email, name, picture, created_at, last_login_at
            ) VALUES ('legacy', NULL, NULL, NULL, '2026-01-01', '2026-01-01')
            """,
        )
        _ = connection.execute(
            """
            INSERT INTO memorial_photos (
                user_id, file_name, stored_path, content_type, taken_at, created_at
            ) VALUES (1, 'old.jpg', '1/old.jpg', 'image/jpeg',
                      '2026-07-01T23:30:00-05:00', '2026-07-01T23:30:00-05:00')
            """,
        )
        _ = connection.execute(
            """
            INSERT INTO memorial_photos (
                user_id, file_name, stored_path, content_type, taken_at, created_at
            ) VALUES (1, 'naive.jpg', '1/naive.jpg', 'image/jpeg',
                      '2026-07-01T12:00:00', '2026-07-01T12:00:00')
            """,
        )
        connection.commit()

    # When: the versioned migration runner initializes the legacy database.
    settings = _settings(db_path)
    database.initialize_database(settings)

    # Then: new required columns are populated without losing the legacy row.
    with contextlib.closing(database.connect(settings)) as connection:
        connection.row_factory = None
        rows = connection.execute(
            """
            SELECT file_name, taken_at_utc, local_date, size_bytes
            FROM memorial_photos ORDER BY file_name
            """,
        ).fetchall()
    assert rows == [
        ("naive.jpg", "2026-07-01T03:00:00.000Z", "2026-07-01", 0),
        ("old.jpg", "2026-07-02T04:30:00.000Z", "2026-07-02", 0),
    ]
    assert database.current_migration_version(settings) == 6


def test_concurrent_initialization_applies_each_migration_once(tmp_path: Path) -> None:
    # Given: several workers sharing one new SQLite path.
    settings = _settings(tmp_path / "shared.db")

    # When: they initialize concurrently.
    with ThreadPoolExecutor(max_workers=8) as executor:
        _ = list(executor.map(database.initialize_database, [settings] * 16))

    # Then: SQLite locking and the ledger serialize migration application.
    assert [version for version, _name in _migration_rows(settings.auth_db_path())] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]


def test_cached_connect_does_not_take_a_migration_write_lock(tmp_path: Path) -> None:
    # Given: this process has initialized the database and another writer is active.
    settings = _settings(tmp_path / "shared.db")
    with contextlib.closing(database.connect(settings)):
        pass
    writer = sqlite3.connect(settings.auth_db_path(), timeout=0.05)
    _ = writer.execute("BEGIN IMMEDIATE")

    try:
        # When: a normal service connection is opened from the initialized process.
        with contextlib.closing(database.connect(settings)) as reader:
            reader.row_factory = None
            value = _fetch_int(reader.execute("SELECT 1"))
    finally:
        writer.rollback()
        writer.close()

    # Then: lazy migration setup did not contend for the existing write lock.
    assert value == (1,)


def test_duplicate_packaged_migration_versions_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: two packaged resources claim the same numeric version.
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    _ = (migration_dir / "006_first.sql").write_text("SELECT 1;", encoding="utf-8")
    _ = (migration_dir / "006_second.sql").write_text("SELECT 2;", encoding="utf-8")
    monkeypatch.setattr(database, "_sql_dir", lambda: migration_dir)

    # When/Then: startup fails instead of silently skipping one script.
    with pytest.raises(ConfigurationError, match="Duplicate migration version 6"):
        database.initialize_database(_settings(tmp_path / "app.db"))


def test_ledger_name_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: a ledger row has the same version as a resource but a different name.
    settings = _settings(tmp_path / "app.db")
    database.initialize_database(settings)
    with contextlib.closing(sqlite3.connect(settings.auth_db_path())) as connection:
        _ = connection.execute(
            "UPDATE schema_migrations SET name = 'renamed.sql' WHERE version = 6",
        )
        connection.commit()
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    _ = (migration_dir / "006_expected.sql").write_text("SELECT 1;", encoding="utf-8")
    monkeypatch.setattr(database, "_sql_dir", lambda: migration_dir)

    # When/Then: the drift is surfaced as a configuration error.
    with pytest.raises(
        ConfigurationError, match="Migration ledger mismatch for version 6"
    ):
        database.initialize_database(settings)
