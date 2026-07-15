from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from importlib.resources import files
from itertools import repeat
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import SecretStr

from chiwawa_backend import config
from chiwawa_backend.config import Settings
from chiwawa_backend.errors import ConfigurationError
from chiwawa_backend.schemas.auth import GoogleUserProfile
from chiwawa_backend.services.auth import save_or_update_user
from chiwawa_backend.state import AppState


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


def test_all_production_migrations_are_package_resources() -> None:
    # Given: the importable backend package.
    sql_dir = files("chiwawa_backend").joinpath("sql")

    # Then: installed production persistence can load every hardening migration.
    assert all(
        sql_dir.joinpath(name).is_file()
        for name in (
            "003_app_state.sql",
            "004_oauth_states.sql",
            "005_memorial_hardening.sql",
            "006_upload_request_slots.sql",
        )
    )


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


def test_photo_relative_path_uses_runtime_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: an installed backend process with a relative photo root.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MEMORIAL_PHOTO_DIR", raising=False)

    # When: the default photo root is resolved.
    photo_path = Settings().photo_dir_path()

    # Then: runtime photos stay under the process working directory.
    assert photo_path == tmp_path / "data" / "memorial_photos"


def test_valid_production_settings_require_explicit_shared_paths(
    tmp_path: Path,
) -> None:
    # Given: complete production credentials and absolute shared storage paths.
    database_path = tmp_path / "production.db"
    photo_path = tmp_path / "photos"
    settings = Settings(
        app_env=config.DeploymentMode.PRODUCTION,
        database_path=database_path,
        memorial_photo_dir=photo_path,
        google_client_id="client-id",
        google_client_secret=SecretStr("client-secret"),
        google_redirect_uri="https://example.test/oauth/callback",
        google_oauth_cookie_secure=True,
        jwt_secret=SecretStr("x" * 32),
    )

    # When: production requirements are validated.
    settings.validate_production()

    # Then: production mode and shared paths are explicit and usable.
    assert settings.is_production
    assert settings.auth_db_path() == database_path
    assert settings.photo_dir_path() == photo_path


def test_production_settings_reject_relative_database_path(tmp_path: Path) -> None:
    # Given: otherwise complete production settings with a relative database path.
    settings = Settings(
        app_env=config.DeploymentMode.PRODUCTION,
        database_path=Path("data/production.db"),
        memorial_photo_dir=tmp_path / "photos",
        google_client_id="client-id",
        google_client_secret=SecretStr("client-secret"),
        google_redirect_uri="https://example.test/oauth/callback",
        google_oauth_cookie_secure=True,
        jwt_secret=SecretStr("x" * 32),
    )

    # When/Then: production validation rejects implicit runtime-relative storage.
    with pytest.raises(ConfigurationError, match="DATABASE_PATH must be absolute"):
        settings.validate_production()


def test_production_settings_reject_insecure_oauth_redirect(tmp_path: Path) -> None:
    settings = Settings(
        app_env=config.DeploymentMode.PRODUCTION,
        database_path=tmp_path / "production.db",
        memorial_photo_dir=tmp_path / "photos",
        google_client_id="client-id",
        google_client_secret=SecretStr("client-secret"),
        google_redirect_uri="http://example.test/oauth/callback",
        google_oauth_cookie_secure=True,
        jwt_secret=SecretStr("x" * 32),
    )

    with pytest.raises(ConfigurationError, match="must use HTTPS"):
        settings.validate_production()


def test_existing_auth_db_permissions_are_restricted(tmp_path: Path) -> None:
    db_path = tmp_path / "google_auth.db"
    db_path.touch(mode=0o644)
    db_path.chmod(0o644)

    _ = save_or_update_user(
        GoogleUserProfile(sub="permission-test-user"),
        Settings(google_auth_db_path=db_path),
    )

    assert db_path.stat().st_mode & 0o777 == 0o600
