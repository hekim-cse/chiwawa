from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from chiwawa_backend.services.local_photo_fs import StoragePathError
from chiwawa_backend.services.local_photo_store import LocalPhotoStore
from tests.memorial_test_support import settings

if TYPE_CHECKING:
    from chiwawa_backend.services.local_photo_store import StagedDelete


def test_store_rejects_filesystem_root_before_mutating_it(tmp_path: Path) -> None:
    # Given: a deployment accidentally points photo storage at the filesystem root.
    active_settings = settings(tmp_path).model_copy(
        update={"memorial_photo_dir": Path("/")},
    )

    # When/Then: construction fails before permissions or entries can be touched.
    with pytest.raises(StoragePathError):
        _ = LocalPhotoStore(active_settings)


def test_store_rejects_database_nested_inside_photo_root(tmp_path: Path) -> None:
    # Given: the database file is configured beneath the recovery-managed photo tree.
    root = tmp_path / "photos"
    active_settings = settings(tmp_path).model_copy(
        update={"google_auth_db_path": root / "app.db"},
    )

    # When/Then: storage rejects the overlap before creating the root.
    with pytest.raises(StoragePathError):
        _ = LocalPhotoStore(active_settings)
    assert not root.exists()


def test_store_rejects_nonexclusive_existing_root(tmp_path: Path) -> None:
    # Given: an existing directory contains an unrelated operator-owned file.
    root = tmp_path / "shared"
    root.mkdir()
    unrelated = root / "do-not-touch.txt"
    _ = unrelated.write_bytes(b"operator data")
    active_settings = settings(tmp_path).model_copy(
        update={"memorial_photo_dir": root},
    )

    # When: the directory is considered as a photo recovery root.
    with pytest.raises(StoragePathError):
        _ = LocalPhotoStore(active_settings)

    # Then: validation fails without changing the unrelated entry.
    assert unrelated.read_bytes() == b"operator data"


def test_save_rejects_root_symlink_swapped_after_construction(
    tmp_path: Path,
) -> None:
    # Given: the configured root is replaced by an outside symlink.
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: "private")
    held_root = tmp_path / "held-root"
    _ = store.root.rename(held_root)
    outside = tmp_path / "outside"
    outside.mkdir()
    store.root.symlink_to(outside, target_is_directory=True)

    # When: a new private photo is saved through the stale store instance.
    with pytest.raises(StoragePathError):
        _ = store.save(7, ".png", b"PRIVATE")

    # Then: the symlink target receives neither a member directory nor bytes.
    assert not (outside / "7").exists()
    assert not any(outside.iterdir())


def test_save_removes_created_file_when_directory_sync_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: the final member-directory sync fails after writing file bytes.
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: "private")
    original_fsync = os.fsync
    calls = 0

    def fail_third_sync(file_descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            message = "injected sync failure"
            raise OSError(message)
        original_fsync(file_descriptor)

    monkeypatch.setattr(os, "fsync", fail_third_sync)

    # When: durable save cannot establish its directory entry.
    with pytest.raises(OSError, match="injected sync failure"):
        _ = store.save(7, ".png", b"PRIVATE")

    # Then: no uncommitted photo file remains for a later DB transaction.
    assert not any((store.root / "7").iterdir())


def test_stage_delete_restores_source_when_directory_sync_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: a stored photo and a failure after staging unlinks the source.
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: "private")
    relative = store.save(7, ".png", b"PRIVATE")
    original_fsync = os.fsync
    calls = 0

    def fail_third_sync(file_descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            message = "injected sync failure"
            raise OSError(message)
        original_fsync(file_descriptor)

    monkeypatch.setattr(os, "fsync", fail_third_sync)

    # When: the staged move cannot be made durable.
    with pytest.raises(OSError, match="injected sync failure"):
        _ = store.stage_delete(relative)

    # Then: the DB-referenced source is restored before the error escapes.
    assert (store.root / relative).read_bytes() == b"PRIVATE"
    assert not (store.root / ".trash" / relative).exists()


def test_stage_delete_retains_trash_when_compensating_link_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: directory sync and the following source-link restoration both fail.
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: "private")
    relative = store.save(7, ".png", b"PRIVATE")
    original_fsync = os.fsync
    original_link = os.link
    sync_calls = 0
    link_calls = 0

    def fail_third_sync(file_descriptor: int) -> None:
        nonlocal sync_calls
        sync_calls += 1
        if sync_calls == 3:
            message = "injected sync failure"
            raise OSError(message)
        original_fsync(file_descriptor)

    def fail_compensating_link(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        nonlocal link_calls
        link_calls += 1
        if link_calls == 2:
            message = "injected restore failure"
            raise OSError(message)
        original_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(os, "fsync", fail_third_sync)
    monkeypatch.setattr(os, "link", fail_compensating_link)

    # When: staging cannot restore the visible source path before returning.
    with pytest.raises(OSError, match="injected sync failure"):
        _ = store.stage_delete(relative)

    # Then: the only durable inode remains in trash for startup recovery.
    assert not (store.root / relative).exists()
    assert (store.root / ".trash" / relative).read_bytes() == b"PRIVATE"


def test_stage_delete_rejects_trash_symlink_swapped_after_construction(
    tmp_path: Path,
) -> None:
    # Given: the private trash directory is replaced by an outside symlink.
    names = iter(("photo", "staged"))
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: next(names))
    relative = store.save(7, ".png", b"private")
    outside = tmp_path / "outside"
    outside.mkdir()
    (store.root / ".trash").rmdir()
    (store.root / ".trash").symlink_to(outside, target_is_directory=True)

    # When: deletion staging opens the swapped trash directory.
    with pytest.raises(StoragePathError):
        _ = store.stage_delete(relative)

    # Then: the source remains private and no bytes reach the outside directory.
    assert (store.root / relative).read_bytes() == b"private"
    assert not any(outside.iterdir())


def test_restore_rejects_root_symlink_swapped_after_staging(tmp_path: Path) -> None:
    # Given: a staged file and a root path redirected to attacker-controlled storage.
    names = iter(("photo", "staged"))
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: next(names))
    relative = store.save(7, ".png", b"private")
    staged = store.stage_delete(relative)
    held_root = tmp_path / "held-root"
    _ = store.root.rename(held_root)
    outside = tmp_path / "outside"
    (outside / ".trash").mkdir(parents=True)
    (outside / "7").mkdir()
    decoy = outside / ".trash" / staged.trash_path.name
    _ = decoy.write_bytes(b"outside")
    store.root.symlink_to(outside, target_is_directory=True)

    # When: restoration reopens the configured root.
    with pytest.raises(StoragePathError):
        store.restore_delete(staged)

    # Then: neither the genuine staged file nor the outside decoy is moved.
    assert (held_root / ".trash" / relative).read_bytes() == b"private"
    assert decoy.read_bytes() == b"outside"
    assert not (outside / relative).exists()


def test_finalize_rejects_trash_symlink_swapped_after_staging(tmp_path: Path) -> None:
    # Given: the trash path is redirected while the genuine staged file is retained.
    names = iter(("photo", "staged"))
    store = LocalPhotoStore(settings(tmp_path), name_factory=lambda: next(names))
    staged = store.stage_delete(store.save(7, ".png", b"private"))
    held_trash = store.root / ".trash-held"
    _ = (store.root / ".trash").rename(held_trash)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "7").mkdir()
    decoy = outside / "7" / staged.trash_path.name
    _ = decoy.write_bytes(b"outside")
    (store.root / ".trash").symlink_to(outside, target_is_directory=True)

    # When: finalization reopens the configured trash directory.
    with pytest.raises(StoragePathError):
        store.finalize_delete(staged)

    # Then: both the private staged bytes and outside decoy remain intact.
    assert (held_trash / "7" / staged.trash_path.name).read_bytes() == b"private"
    assert decoy.read_bytes() == b"outside"


def test_simultaneous_same_trash_name_preserves_both_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: two stores stage different files under the same generated trash name.
    active_settings = settings(tmp_path)
    stores = (
        LocalPhotoStore(active_settings, name_factory=lambda: "collision"),
        LocalPhotoStore(active_settings, name_factory=lambda: "collision"),
    )
    relatives = (
        stores[0].save(7, ".png", b"first"),
        stores[1].save(8, ".png", b"second"),
    )
    trash_target = stores[0].root / ".trash" / "collision"
    original_exists = Path.exists

    def expose_race_window(path: Path) -> bool:
        if path == trash_target:
            return False
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", expose_race_window)

    def stage(index: int) -> StagedDelete:
        return stores[index].stage_delete(relatives[index])

    # When: both deletion operations contend concurrently.
    with ThreadPoolExecutor(max_workers=2) as executor:
        staged = list(executor.map(stage, (0, 1)))

    # Then: reversible per-user trash paths retain both source payloads.
    assert len({item.trash_path for item in staged}) == 2
    assert sorted(item.trash_path.read_bytes() for item in staged) == [
        b"first",
        b"second",
    ]


@pytest.mark.parametrize("user_part", [str(1 << 63), "9" * 5000])
def test_relative_path_rejects_oversized_user_identifiers(
    tmp_path: Path,
    user_part: str,
) -> None:
    # Given: a path contains a numeric component outside SQLite's ID domain.
    store = LocalPhotoStore(settings(tmp_path))

    # When/Then: bounded parsing converts both overflow forms to a storage error.
    with pytest.raises(StoragePathError):
        _ = store.resolve(Path(user_part, "photo.png"))
