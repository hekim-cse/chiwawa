from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from importlib.resources import files
from itertools import repeat
from typing import TYPE_CHECKING
from uuid import UUID

from chiwawa_backend.config import Settings
from chiwawa_backend.schemas.auth import GoogleUserProfile
from chiwawa_backend.services.auth import save_or_update_user
from chiwawa_backend.state import AppState

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_app_state_allocates_concurrency_safe_uuid_ids() -> None:
    # Given: many workers allocating identifiers from one development state store.
    state = AppState()
    with ThreadPoolExecutor(max_workers=16) as executor:
        identifiers = list(executor.map(state.next_id, repeat("trip", 512)))

    # Then: every identifier is unique without a shared numeric counter race.
    assert len(set(identifiers)) == len(identifiers)
    for identifier in identifiers:
        _ = UUID(identifier.removeprefix("trip_"))


def test_sqlite_schema_is_a_package_resource() -> None:
    # Given: the importable backend package.
    schema = files("chiwawa_backend").joinpath("sql", "001_google_users.sql")

    # Then: installed auth persistence can load its schema without repository files.
    assert schema.is_file()


def test_auth_db_relative_path_uses_runtime_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: an installed backend process running outside the source tree.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GOOGLE_AUTH_DB_PATH", raising=False)

    # When: the default relative auth database path is resolved.
    db_path = Settings().auth_db_path()

    # Then: runtime data stays under the process working directory.
    assert db_path == tmp_path / "data" / "google_auth.db"


def test_existing_auth_db_permissions_are_restricted(tmp_path: Path) -> None:
    db_path = tmp_path / "google_auth.db"
    db_path.touch(mode=0o644)
    db_path.chmod(0o644)

    _ = save_or_update_user(
        GoogleUserProfile(sub="permission-test-user"),
        Settings(google_auth_db_path=db_path),
    )

    assert db_path.stat().st_mode & 0o777 == 0o600
