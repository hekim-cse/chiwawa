from __future__ import annotations

import contextlib
import datetime as dt
import sqlite3
from typing import TYPE_CHECKING, cast

from chiwawa_backend.errors import ConfigurationError
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.local_photo_fs import StoragePathError
from chiwawa_backend.services.local_photo_inventory import scan_photo_inventory
from chiwawa_backend.services.local_photo_store import LocalPhotoStore

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.config import Settings


def reconcile_memorial_photos(settings: Settings) -> dt.datetime | None:
    store = LocalPhotoStore(settings)
    with contextlib.closing(connect(settings)) as connection:
        _ = connection.execute("BEGIN IMMEDIATE")
        try:
            active_uploads = _active_uploads(connection)
            references = _referenced_paths(connection, store)
            inventory = scan_photo_inventory(store)
            final_files = set(inventory.final_files)
            for staged in inventory.staged_deletes:
                if (
                    staged.original_path not in references
                    or staged.original_path in final_files
                ):
                    store.finalize_delete(staged)
                else:
                    store.restore_delete(staged)
                    final_files.add(staged.original_path)
            if not active_uploads:
                for relative in final_files - references:
                    store.discard(relative)
            missing_references = references - final_files
            if missing_references:
                raise StoragePathError(min(missing_references))
            active_until = _extend_active_uploads(
                connection,
                settings,
                active_uploads,
            )
            connection.commit()
        except (OSError, sqlite3.Error):
            connection.rollback()
            raise
    return active_until


def _referenced_paths(
    connection: sqlite3.Connection,
    store: LocalPhotoStore,
) -> set[Path]:
    rows = cast(
        "list[sqlite3.Row]",
        connection.execute(
            "SELECT user_id, stored_path FROM memorial_photos",
        ).fetchall(),
    )
    references: set[Path] = set()
    for row in rows:
        stored_path = cast("str | int | float | None", row["stored_path"])
        if not isinstance(stored_path, str):
            message = "memorial stored_path must be text"
            raise ConfigurationError(message)
        user_id = cast("str | int | float | None", row["user_id"])
        if not isinstance(user_id, int):
            message = "memorial user_id must be an integer"
            raise ConfigurationError(message)
        references.add(store.parse_user_stored_path(user_id, stored_path))
    return references


def _active_uploads(
    connection: sqlite3.Connection,
) -> list[tuple[str, dt.datetime]]:
    message = "invalid active upload lease expiration"
    now = dt.datetime.now(dt.UTC).isoformat()
    rows = cast(
        "list[sqlite3.Row]",
        connection.execute(
            "SELECT lease_id, expires_at FROM upload_leases WHERE expires_at > ?",
            (now,),
        ).fetchall(),
    )
    active_uploads: list[tuple[str, dt.datetime]] = []
    for row in rows:
        lease_id = cast("str | int | float | None", row["lease_id"])
        value = cast("str | int | float | None", row["expires_at"])
        if not isinstance(lease_id, str) or not isinstance(value, str):
            raise ConfigurationError(message)
        try:
            expiration = dt.datetime.fromisoformat(value)
        except ValueError as error:
            raise ConfigurationError(message) from error
        if expiration.tzinfo is None or expiration.utcoffset() is None:
            raise ConfigurationError(message)
        active_uploads.append((lease_id, expiration.astimezone(dt.UTC)))
    return active_uploads


def _extend_active_uploads(
    connection: sqlite3.Connection,
    settings: Settings,
    active_uploads: list[tuple[str, dt.datetime]],
) -> dt.datetime | None:
    if not active_uploads:
        return None
    protected_until = dt.datetime.now(dt.UTC) + dt.timedelta(
        seconds=settings.upload_lease_ttl_seconds,
    )
    expirations: list[dt.datetime] = []
    for lease_id, expiration in active_uploads:
        extended = max(expiration, protected_until)
        _ = connection.execute(
            "UPDATE upload_leases SET expires_at = ? WHERE lease_id = ?",
            (extended.isoformat(), lease_id),
        )
        expirations.append(extended)
    return min(expirations)
