from __future__ import annotations

import contextlib
import datetime as dt
import os
import sqlite3
import stat
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread
from typing import TYPE_CHECKING, cast, override

import pytest

from chiwawa_backend.errors import NotFoundError
from chiwawa_backend.services import memorial_photos
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.local_photo_fs import StoragePathError
from chiwawa_backend.services.local_photo_inventory import scan_photo_inventory
from chiwawa_backend.services.local_photo_store import LocalPhotoStore
from chiwawa_backend.services.memorial_photo_recovery import (
    reconcile_memorial_photos,
)
from tests.memorial_test_support import admission, insert_photo, insert_user, settings

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.services.local_photo_inventory import PhotoInventory
    from chiwawa_backend.services.local_photo_store import StagedDelete


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_startup_preserves_unreferenced_file_while_upload_lease_is_active(
    tmp_path: Path,
) -> None:
    # Given: a ready worker saved bytes under a still-active durable upload lease.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    active_admission = admission(
        active_settings,
        lease_id="in-flight",
        clock=lambda: dt.datetime(2099, 1, 1, tzinfo=dt.UTC),
    )
    lease = active_admission.acquire(user_id, 7)
    store = LocalPhotoStore(active_settings, name_factory=lambda: "inflight")
    relative = store.save(user_id, ".png", b"inflight")

    # When: a sibling worker runs startup recovery before metadata insertion.
    _ = reconcile_memorial_photos(active_settings)

    # Then: recovery preserves the in-flight bytes until the lease is released.
    assert store.resolve(relative).read_bytes() == b"inflight"
    active_admission.release(lease)
    _ = reconcile_memorial_photos(active_settings)
    assert not (store.root / relative).exists()


def test_startup_removes_legacy_readiness_probe_without_blocking(
    tmp_path: Path,
) -> None:
    # Given: an older worker crashed after creating a root-level readiness probe.
    active_settings = settings(tmp_path)
    store = LocalPhotoStore(active_settings)
    stale_probe = store.root / ".ready-stale"
    _ = stale_probe.write_bytes(b"")

    # When: a current worker inventories its dedicated local photo root.
    _ = reconcile_memorial_photos(active_settings)

    # Then: the legacy regular probe is discarded and startup completes.
    assert not stale_probe.exists()


def test_slow_recovery_extends_lease_before_releasing_database_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: an active one-second lease and a filesystem inventory that takes longer.
    active_settings = settings(tmp_path, upload_lease_ttl_seconds=1)
    user_id = insert_user(active_settings)
    active_admission = admission(
        active_settings,
        lease_id="slow-recovery",
        clock=lambda: dt.datetime.now(dt.UTC),
    )
    _lease = active_admission.acquire(user_id, 7)
    store = LocalPhotoStore(active_settings, name_factory=lambda: "inflight")
    relative = store.save(user_id, ".png", b"inflight")
    original_scan = scan_photo_inventory

    def slow_scan(active_store: LocalPhotoStore) -> PhotoInventory:
        time.sleep(1.1)
        return original_scan(active_store)

    monkeypatch.setattr(
        "chiwawa_backend.services.memorial_photo_recovery.scan_photo_inventory",
        slow_scan,
    )

    # When: recovery holds the writer lock beyond the lease's original expiry.
    active_until = reconcile_memorial_photos(active_settings)

    # Then: it preserves the in-flight file and renews protection before commit.
    assert (store.root / relative).read_bytes() == b"inflight"
    assert active_until is not None
    assert active_until > dt.datetime.now(dt.UTC)


def test_startup_repairs_existing_final_and_trash_permissions(tmp_path: Path) -> None:
    # Given: final and staged private content was externally made host-readable.
    active_settings = settings(tmp_path)
    final_user = insert_user(active_settings, "final")
    staged_user = insert_user(active_settings, "staged")
    _final_photo, final_path = insert_photo(
        active_settings,
        final_user,
        size_bytes=5,
    )
    _staged_photo, staged_path = insert_photo(
        active_settings,
        staged_user,
        size_bytes=6,
    )
    store = LocalPhotoStore(active_settings)
    staged = store.stage_delete(staged_path)
    (store.root / str(final_user)).chmod(0o777)
    (store.root / final_path).chmod(0o666)
    (store.root / ".trash" / str(staged_user)).chmod(0o777)
    staged.trash_path.chmod(0o666)

    # When: startup inventories and restores the referenced staged file.
    _ = reconcile_memorial_photos(active_settings)

    # Then: both the member directory and restored file are private again.
    assert _mode(store.root / str(final_user)) == 0o700
    assert _mode(store.root / final_path) == 0o600
    assert _mode(store.root / str(staged_user)) == 0o700
    assert _mode(store.root / staged_path) == 0o600


def test_startup_rejects_fifo_without_blocking(tmp_path: Path) -> None:
    # Given: a numeric member directory contains a FIFO disguised as an image.
    active_settings = settings(tmp_path)
    store = LocalPhotoStore(active_settings)
    member_dir = store.root / "7"
    member_dir.mkdir()
    os.mkfifo(member_dir / "blocked.png")
    outcome: list[type[BaseException] | None] = []

    def recover() -> None:
        try:
            _ = reconcile_memorial_photos(active_settings)
        except OSError as error:
            outcome.append(type(error))
        else:
            outcome.append(None)

    # When: startup inventory opens the non-regular entry.
    worker = Thread(target=recover, daemon=True)
    worker.start()
    worker.join(timeout=0.25)

    # Then: it fails closed promptly instead of blocking on FIFO open.
    assert not worker.is_alive()
    assert outcome == [StoragePathError]


def test_startup_rejects_stored_path_owned_by_another_user(tmp_path: Path) -> None:
    # Given: user A's row was corrupted to reference user B's private file path.
    active_settings = settings(tmp_path)
    first_user = insert_user(active_settings, "first")
    second_user = insert_user(active_settings, "second")
    _second_photo, second_path = insert_photo(
        active_settings,
        second_user,
        size_bytes=6,
    )
    first_photo, first_path = insert_photo(
        active_settings,
        first_user,
        size_bytes=4,
        name="first",
    )
    with contextlib.closing(connect(active_settings)) as connection, connection:
        _ = connection.execute(
            "UPDATE memorial_photos SET stored_path = ? WHERE id = ?",
            (second_path.as_posix(), first_photo),
        )
    (LocalPhotoStore(active_settings).root / first_path).unlink()

    # When/Then: startup and direct file access both fail closed.
    with pytest.raises(StoragePathError):
        _ = reconcile_memorial_photos(active_settings)
    with pytest.raises(NotFoundError):
        _ = memorial_photos.photo_file(
            first_user,
            first_photo,
            settings=active_settings,
        )


def test_photo_file_maps_disappearance_after_resolution_to_not_found(
    tmp_path: Path,
) -> None:
    # Given: a photo disappears after secure resolution but before size backfill.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    photo_id, relative = insert_photo(active_settings, user_id, size_bytes=5)

    class VanishingStore(LocalPhotoStore):
        @override
        def read(self, relative_path: str | Path) -> bytes:
            relative = self.parse_stored_path(relative_path)
            (self.root / relative).unlink()
            return super().read(relative)

    # When/Then: the download boundary keeps the race private as a stable 404.
    with pytest.raises(NotFoundError):
        _ = memorial_photos.photo_file(
            user_id,
            photo_id,
            settings=active_settings,
            store=VanishingStore(active_settings),
        )
    assert not (LocalPhotoStore(active_settings).root / relative).exists()


def test_photo_file_response_survives_unlink_after_descriptor_read(
    tmp_path: Path,
) -> None:
    # Given: deletion removes the directory entry immediately after a secure read.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    photo_id, relative = insert_photo(active_settings, user_id, size_bytes=5)

    class UnlinkedAfterReadStore(LocalPhotoStore):
        @override
        def read(self, relative_path: str | Path) -> bytes:
            parsed = self.parse_stored_path(relative_path)
            data = super().read(parsed)
            (self.root / parsed).unlink()
            return data

    # When: the service finishes the read before returning the HTTP payload.
    data, content_type = memorial_photos.photo_file(
        user_id,
        photo_id,
        settings=active_settings,
        store=UnlinkedAfterReadStore(active_settings),
    )

    # Then: response bytes remain complete without reopening a pathname.
    assert data == b"x" * 5
    assert content_type == "image/png"
    assert not (LocalPhotoStore(active_settings).root / relative).exists()


def test_delete_holds_database_lock_while_file_is_staged(tmp_path: Path) -> None:
    # Given: deletion pauses after staging while a sibling recovery tries to start.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    photo_id, relative = insert_photo(active_settings, user_id, size_bytes=5)
    staged = Event()
    allow_delete = Event()
    recovery_started = Event()
    recovery_completed = Event()

    class BlockingStore(LocalPhotoStore):
        @override
        def stage_delete(self, relative_path: str | Path) -> StagedDelete:
            result = super().stage_delete(relative_path)
            staged.set()
            assert allow_delete.wait(timeout=2)
            return result

    def recover() -> None:
        recovery_started.set()
        _ = reconcile_memorial_photos(active_settings)
        recovery_completed.set()

    # When: recovery contends during the filesystem/DB delete boundary.
    with ThreadPoolExecutor(max_workers=2) as executor:
        deleting = executor.submit(
            memorial_photos.delete_photo,
            user_id,
            photo_id,
            settings=active_settings,
            store=BlockingStore(active_settings),
        )
        assert staged.wait(timeout=2)
        recovering = executor.submit(recover)
        assert recovery_started.wait(timeout=2)
        assert not recovery_completed.wait(timeout=0.1)
        allow_delete.set()
        deleting.result(timeout=2)
        recovering.result(timeout=2)

    # Then: no metadata, final file, or staged file survives the serialization.
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path()),
    ) as connection:
        row = cast(
            "tuple[int] | None",
            connection.execute(
                "SELECT id FROM memorial_photos WHERE id = ?",
                (photo_id,),
            ).fetchone(),
        )
    assert row is None
    assert not (LocalPhotoStore(active_settings).root / relative).exists()
    assert not any((LocalPhotoStore(active_settings).root / ".trash").iterdir())
