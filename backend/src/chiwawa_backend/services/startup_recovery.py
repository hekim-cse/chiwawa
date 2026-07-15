from __future__ import annotations

import datetime as dt
import sqlite3
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Final

from anyio import create_task_group, sleep
from anyio.to_thread import run_sync

from chiwawa_backend.services.database import DatabasePathUnavailableError
from chiwawa_backend.services.local_photo_fs import StoragePathError
from chiwawa_backend.services.memorial_photo_recovery import (
    reconcile_memorial_photos,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable
    from contextlib import AbstractAsyncContextManager

    from fastapi import FastAPI

    from chiwawa_backend.config import Settings
    from chiwawa_backend.services.readiness import StartupRecoveryStatus

RECOVERY_RETRY_SECONDS: Final = 1.0
EXPIRATION_GRACE_SECONDS: Final = 0.01


def create_application_lifespan(
    settings: Settings,
    status: StartupRecoveryStatus,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        active_until = await run_sync(_reconcile_or_defer, settings, status)
        async with create_task_group() as task_group:
            if not status.completed or active_until is not None:
                _ = task_group.start_soon(
                    _maintain_reconciliation,
                    settings,
                    status,
                    active_until,
                )
            try:
                yield
            finally:
                task_group.cancel_scope.cancel()

    return lifespan


def _reconcile_or_defer(
    settings: Settings,
    status: StartupRecoveryStatus,
) -> dt.datetime | None:
    try:
        active_until = reconcile_memorial_photos(settings)
    except StoragePathError as error:
        root = settings.photo_dir_path()
        if error.path not in {root, root / ".trash"}:
            raise
        status.mark_incomplete()
        return None
    except (DatabasePathUnavailableError, sqlite3.OperationalError):
        status.mark_incomplete()
        return None
    status.mark_completed()
    return active_until


async def _maintain_reconciliation(
    settings: Settings,
    status: StartupRecoveryStatus,
    active_until: dt.datetime | None,
) -> None:
    next_expiration = active_until
    while not status.completed or next_expiration is not None:
        if status.completed and next_expiration is not None:
            delay = (next_expiration - dt.datetime.now(dt.UTC)).total_seconds()
            await sleep(max(delay + EXPIRATION_GRACE_SECONDS, 0.01))
        else:
            await sleep(RECOVERY_RETRY_SECONDS)
        next_expiration = await run_sync(_reconcile_or_defer, settings, status)
