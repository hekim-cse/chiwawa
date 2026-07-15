from __future__ import annotations

import contextlib
import os
import shutil
import sqlite3
from typing import TYPE_CHECKING, cast, final
from uuid import uuid4

from chiwawa_backend.errors import ConfigurationError, ServiceUnavailableError
from chiwawa_backend.services.database import (
    connect,
    current_migration_version,
    latest_migration_version,
)
from chiwawa_backend.services.local_photo_store import LocalPhotoStore

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.config import Settings

READINESS_FAILURE_DETAIL = "service dependencies unavailable"


@final
class StartupRecoveryStatus:
    __slots__ = ("_completed",)

    def __init__(self) -> None:
        self._completed = False

    @property
    def completed(self) -> bool:
        return self._completed

    def mark_completed(self) -> None:
        self._completed = True

    def mark_incomplete(self) -> None:
        self._completed = False


def check_readiness(
    settings: Settings,
    startup_recovery: StartupRecoveryStatus,
) -> None:
    try:
        settings.validate_production()
        _check_database(settings)
        store = LocalPhotoStore(settings)
        _check_photo_root(store.root)
        _check_disk(store.root, settings.min_free_disk_bytes)
        _check_startup_recovery(startup_recovery)
    except (ConfigurationError, OSError, sqlite3.Error) as error:
        raise ServiceUnavailableError(READINESS_FAILURE_DETAIL) from error


def _check_startup_recovery(startup_recovery: StartupRecoveryStatus) -> None:
    if not startup_recovery.completed:
        raise ConfigurationError(READINESS_FAILURE_DETAIL)


def _check_database(settings: Settings) -> None:
    with contextlib.closing(connect(settings)) as connection:
        row = cast("tuple[int] | None", connection.execute("SELECT 1").fetchone())
    if row is None or row[0] != 1:
        raise ConfigurationError(READINESS_FAILURE_DETAIL)
    if current_migration_version(settings) != latest_migration_version():
        raise ConfigurationError(READINESS_FAILURE_DETAIL)


def _check_photo_root(root: Path) -> None:
    probe = root / ".health" / uuid4().hex
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_descriptor = os.open(probe, flags, 0o600)
    try:
        os.fchmod(file_descriptor, 0o600)
    finally:
        os.close(file_descriptor)
        probe.unlink()


def _check_disk(root: Path, minimum_free_bytes: int) -> None:
    if shutil.disk_usage(root).free < minimum_free_bytes:
        raise OSError(READINESS_FAILURE_DETAIL)
