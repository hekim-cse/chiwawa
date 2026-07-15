from __future__ import annotations

import contextlib
import os
import sqlite3
import stat
from typing import TYPE_CHECKING, cast

import pytest

from chiwawa_backend.services import memorial_photo_lifecycle, memorial_photos
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.local_photo_fs import StoragePathError
from chiwawa_backend.services.local_photo_store import LocalPhotoStore
from chiwawa_backend.services.memorial_photos import photo_file
from tests.memorial_test_support import insert_photo, insert_user, settings

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.services.local_photo_store import StagedDelete


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_save_repairs_permissions_and_returns_relative_path(tmp_path: Path) -> None:
    # Given: pre-existing permissive local photo directories under umask zero.
    active_settings = settings(tmp_path)
    root = active_settings.photo_dir_path()
    (root / ".trash").mkdir(parents=True)
    root.chmod(0o777)
    (root / ".trash").chmod(0o777)
    original_umask = os.umask(0)
    try:
        store = LocalPhotoStore(active_settings, name_factory=lambda: "fixed")

        # When: a detected PNG is stored for a member.
        relative = store.save(7, ".png", b"private-photo")
    finally:
        _ = os.umask(original_umask)

    # Then: only a relative identifier escapes and every permission is private.
    assert relative.as_posix() == "7/fixed.png"
    assert not relative.is_absolute()
    assert _mode(root) == 0o700
    assert _mode(root / ".trash") == 0o700
    assert _mode(root / "7") == 0o700
    assert _mode(store.resolve(relative)) == 0o600


def test_atomic_save_never_overwrites_existing_file(tmp_path: Path) -> None:
    # Given: a deterministic name already exists in the private store.
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: "collision")
    relative = store.save(3, ".jpg", b"first")

    # When/Then: the exclusive create rejects reuse and preserves prior bytes.
    with pytest.raises(FileExistsError):
        _ = store.save(3, ".jpg", b"second")
    assert store.resolve(relative).read_bytes() == b"first"


@pytest.mark.parametrize("user_id", [-1, 0, 1 << 63])
def test_save_rejects_user_ids_outside_sqlite_range(
    tmp_path: Path,
    user_id: int,
) -> None:
    # Given: a private store and a user identifier SQLite cannot persist safely.
    store = LocalPhotoStore(settings(tmp_path))

    # When/Then: validation happens before any member directory is created.
    with pytest.raises(StoragePathError):
        _ = store.save(user_id, ".png", b"data")
    assert not (store.root / str(user_id)).exists()


@pytest.mark.parametrize(
    "unsafe",
    ["ABSOLUTE", "../outside.png", "7/../../outside.png", ".trash/x"],
)
def test_resolve_rejects_absolute_traversal_and_trash_paths(
    tmp_path: Path,
    unsafe: str,
) -> None:
    # Given: a confined local photo root.
    store = LocalPhotoStore(settings(tmp_path))
    unsafe_path = str(tmp_path / "outside.png") if unsafe == "ABSOLUTE" else unsafe

    # When/Then: paths outside the public member namespace are rejected.
    with pytest.raises(StoragePathError):
        _ = store.resolve(unsafe_path)


def test_resolve_rejects_symlink_component_and_repairs_file_mode(
    tmp_path: Path,
) -> None:
    # Given: one valid file and a user directory symlink aimed outside the root.
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: "photo")
    relative = store.save(7, ".png", b"data")
    stored = settings_root = store.resolve(relative)
    stored.chmod(0o666)
    outside = tmp_path / "outside"
    outside.mkdir()
    (store.root / "8").symlink_to(outside, target_is_directory=True)

    # When: the valid file and symlink path are resolved.
    resolved = store.resolve(relative)

    # Then: valid file mode is repaired and the symlink escape fails closed.
    assert resolved == settings_root
    assert _mode(resolved) == 0o600
    with pytest.raises(StoragePathError):
        _ = store.resolve("8/stolen.png")


def test_legacy_absolute_path_is_normalized_only_inside_root(tmp_path: Path) -> None:
    # Given: a regular legacy file inside the configured root and one outside it.
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: "legacy")
    relative = store.save(9, ".png", b"legacy")
    absolute = store.resolve(relative)
    outside = tmp_path / "outside.png"
    _ = outside.write_bytes(b"outside")

    # When/Then: the confined absolute path migrates, arbitrary absolute does not.
    assert store.normalize_stored_path(absolute) == relative
    with pytest.raises(StoragePathError):
        _ = store.normalize_stored_path(outside)


def test_staged_delete_can_restore_or_finalize_without_cross_device_copy(
    tmp_path: Path,
) -> None:
    # Given: two stored files in the same local filesystem.
    names = iter(("restore", "finalize", "trash-a", "trash-b"))
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: next(names))
    restored_relative = store.save(4, ".png", b"restore")
    finalized_relative = store.save(4, ".png", b"finalize")

    # When: one staged deletion is restored and another finalized.
    restored = store.stage_delete(restored_relative)
    assert not (store.root / restored_relative).exists()
    store.restore_delete(restored)
    finalized = store.stage_delete(finalized_relative)
    trash_path = finalized.trash_path
    store.finalize_delete(finalized)

    # Then: restore is retriable and finalize removes only the trash entry.
    assert store.resolve(restored_relative).read_bytes() == b"restore"
    assert not trash_path.exists()
    assert not (store.root / finalized_relative).exists()


def test_photo_file_normalizes_legacy_row_and_backfills_size(tmp_path: Path) -> None:
    # Given: a migrated row still stores an absolute path and zero size.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    store = LocalPhotoStore(active_settings, name_factory=lambda: "legacy")
    relative = store.save(user_id, ".png", b"legacy-bytes")
    absolute = store.resolve(relative)
    with contextlib.closing(connect(active_settings)) as connection, connection:
        cursor = connection.execute(
            """
            INSERT INTO memorial_photos (
                user_id, file_name, stored_path, content_type, taken_at,
                created_at, taken_at_utc, local_date, size_bytes
            ) VALUES (?, 'legacy.png', ?, 'image/png', '2026-07-01T12:00:00+09:00',
                      '2026-07-01T03:00:00Z', '2026-07-01T03:00:00Z',
                      '2026-07-01', 0)
            """,
            (user_id, str(absolute)),
        )
        photo_id = cursor.lastrowid
    assert photo_id is not None

    # When: the service resolves the legacy row through the active settings.
    data, content_type = photo_file(
        user_id,
        photo_id,
        settings=active_settings,
        store=store,
    )

    # Then: the row is normalized and its real size is persisted for quota accounting.
    assert data == b"legacy-bytes"
    assert content_type == "image/png"
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        row = cast(
            "tuple[str, int] | None",
            connection.execute(
                "SELECT stored_path, size_bytes FROM memorial_photos WHERE id = ?",
                (photo_id,),
            ).fetchone(),
        )
    assert row == (relative.as_posix(), len(b"legacy-bytes"))


def test_store_rejects_root_symlink(tmp_path: Path) -> None:
    # Given: the configured root itself is a symlink to another directory.
    active_settings = settings(tmp_path)
    outside = tmp_path / "outside-root"
    outside.mkdir()
    _ = active_settings.photo_dir_path().symlink_to(
        outside,
        target_is_directory=True,
    )

    # When/Then: constructing the store fails before any path can be trusted.
    with pytest.raises(StoragePathError):
        _ = LocalPhotoStore(active_settings)


def test_database_delete_failure_restores_file_and_preserves_row(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: a persisted photo whose database deletion will fail after trash staging.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    photo_id, relative = insert_photo(active_settings, user_id, size_bytes=6)
    store = LocalPhotoStore(active_settings)

    def fail_delete(
        _connection: sqlite3.Connection,
        _user_id: int,
        _photo_id: int,
    ) -> bool:
        message = "database delete failed"
        raise sqlite3.OperationalError(message)

    monkeypatch.setattr(memorial_photo_lifecycle, "_delete_photo_row", fail_delete)

    # When: the service attempts the coordinated deletion.
    with pytest.raises(sqlite3.OperationalError):
        memorial_photos.delete_photo(
            user_id,
            photo_id,
            settings=active_settings,
            store=store,
        )

    # Then: the original file and row remain retriable with no orphaned trash entry.
    assert store.resolve(relative).read_bytes() == b"x" * 6
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        row = cast(
            "tuple[int] | None",
            connection.execute(
                "SELECT id FROM memorial_photos WHERE id = ?",
                (photo_id,),
            ).fetchone(),
        )
    assert row == (photo_id,)
    assert not any((store.root / ".trash").iterdir())


def test_finalize_failure_keeps_private_trash_after_database_commit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: database deletion succeeds but best-effort trash unlink fails.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    photo_id, _relative = insert_photo(active_settings, user_id, size_bytes=4)
    store = LocalPhotoStore(active_settings)

    def fail_finalize(_staged: StagedDelete) -> None:
        message = "unlink failed"
        raise OSError(message)

    monkeypatch.setattr(store, "finalize_delete", fail_finalize)

    # When: the service deletes the photo.
    memorial_photos.delete_photo(
        user_id,
        photo_id,
        settings=active_settings,
        store=store,
    )

    # Then: metadata is gone while the residual file stays in private trash.
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        row = cast(
            "tuple[int] | None",
            connection.execute(
                "SELECT id FROM memorial_photos WHERE id = ?",
                (photo_id,),
            ).fetchone(),
        )
    trash = store.root / ".trash"
    assert row is None
    assert _mode(trash) == 0o700
    assert len(list(trash.iterdir())) == 1
