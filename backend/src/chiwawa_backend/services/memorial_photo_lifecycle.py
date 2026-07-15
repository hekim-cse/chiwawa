from __future__ import annotations

import contextlib
import sqlite3
from typing import TYPE_CHECKING, cast

from chiwawa_backend.errors import ConfigurationError, NotFoundError
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.local_photo_store import LocalPhotoStore

if TYPE_CHECKING:
    from chiwawa_backend.config import Settings
    from chiwawa_backend.services.local_photo_store import StagedDelete


def delete_photo(
    user_id: int,
    photo_id: int,
    settings: Settings,
    store: LocalPhotoStore | None = None,
) -> None:
    active_store = store or LocalPhotoStore(settings)
    staged: StagedDelete | None = None
    with contextlib.closing(connect(settings)) as connection:
        _ = connection.execute("BEGIN IMMEDIATE")
        try:
            stored_path = _stored_path(connection, user_id, photo_id)
            relative = active_store.normalize_user_stored_path(user_id, stored_path)
            staged = active_store.stage_delete(relative)
            _require_deleted(
                _delete_photo_row(connection, user_id, photo_id),
                photo_id,
            )
            connection.commit()
        except (ConfigurationError, NotFoundError, OSError, sqlite3.Error):
            try:
                if staged is not None:
                    active_store.restore_delete(staged)
            finally:
                connection.rollback()
            raise
    with contextlib.suppress(OSError):
        active_store.finalize_delete(staged)


def _stored_path(
    connection: sqlite3.Connection,
    user_id: int,
    photo_id: int,
) -> str:
    row = cast(
        "sqlite3.Row | None",
        connection.execute(
            "SELECT stored_path FROM memorial_photos WHERE id = ? AND user_id = ?",
            (photo_id, user_id),
        ).fetchone(),
    )
    if row is None:
        raise NotFoundError(entity="memorial_photo", entity_id=str(photo_id))
    value = cast("str | int | float | None", row["stored_path"])
    if not isinstance(value, str):
        message = "memorial stored_path must be text"
        raise ConfigurationError(message)
    return value


def _delete_photo_row(
    connection: sqlite3.Connection,
    user_id: int,
    photo_id: int,
) -> bool:
    cursor = connection.execute(
        "DELETE FROM memorial_photos WHERE id = ? AND user_id = ?",
        (photo_id, user_id),
    )
    return cursor.rowcount == 1


def _require_deleted(deleted: bool, photo_id: int) -> None:
    if not deleted:
        raise NotFoundError(entity="memorial_photo", entity_id=str(photo_id))
