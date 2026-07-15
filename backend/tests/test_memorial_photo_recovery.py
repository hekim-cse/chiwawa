from __future__ import annotations

import contextlib
import datetime as dt
from http import HTTPStatus
from typing import TYPE_CHECKING

import anyio
import pytest
from httpx import ASGITransport, AsyncClient

from chiwawa_backend.errors import ConfigurationError
from chiwawa_backend.main import create_app
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.local_photo_fs import StoragePathError
from chiwawa_backend.services.local_photo_store import LocalPhotoStore
from tests.memorial_test_support import admission, insert_photo, insert_user, settings

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.config import Settings

pytestmark = pytest.mark.anyio


async def _start_app(active_settings: Settings) -> int:
    app = create_app(settings=active_settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client,
    ):
        response = await client.get("/health")
    return response.status_code


async def test_startup_restores_staged_file_when_metadata_row_exists(
    tmp_path: Path,
) -> None:
    # Given: a crash occurs after staging a persisted photo but before row deletion.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    _photo_id, relative = insert_photo(active_settings, user_id, size_bytes=7)
    store = LocalPhotoStore(active_settings)
    staged = store.stage_delete(relative)

    # When: a new application instance completes its startup lifespan.
    status_code = await _start_app(active_settings)

    # Then: the reversible trash entry is restored and metadata remains readable.
    assert status_code == HTTPStatus.OK
    assert staged.trash_path == store.root / ".trash" / str(user_id) / relative.name
    assert store.resolve(relative).read_bytes() == b"x" * 7
    assert not staged.trash_path.exists()


async def test_startup_removes_unreferenced_file_from_interrupted_insert(
    tmp_path: Path,
) -> None:
    # Given: a crash occurs after local save but before metadata insertion.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    store = LocalPhotoStore(active_settings, name_factory=lambda: "orphan")
    relative = store.save(user_id, ".png", b"orphan")

    # When: the next application instance starts.
    status_code = await _start_app(active_settings)

    # Then: the unreferenced final file is removed from private storage.
    assert status_code == HTTPStatus.OK
    assert not (store.root / relative).exists()


async def test_startup_finalizes_staged_file_when_metadata_row_is_absent(
    tmp_path: Path,
) -> None:
    # Given: a crash occurs after metadata deletion but before trash finalization.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    store = LocalPhotoStore(active_settings, name_factory=lambda: "deleted")
    staged = store.stage_delete(store.save(user_id, ".png", b"deleted"))

    # When: the next application instance starts.
    status_code = await _start_app(active_settings)

    # Then: the unreferenced staged entry is finalized idempotently.
    assert status_code == HTTPStatus.OK
    assert not staged.trash_path.exists()


async def test_two_startup_workers_reconcile_the_same_stage_idempotently(
    tmp_path: Path,
) -> None:
    # Given: two workers start against one database and one staged persisted file.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    _photo_id, relative = insert_photo(active_settings, user_id, size_bytes=5)
    store = LocalPhotoStore(active_settings)
    staged = store.stage_delete(relative)

    # When: both application lifespans reconcile concurrently.
    statuses: list[int] = []

    async def start_worker() -> None:
        statuses.append(await _start_app(active_settings))

    async with anyio.create_task_group() as task_group:
        _ = task_group.start_soon(start_worker)
        _ = task_group.start_soon(start_worker)

    # Then: both startups succeed and exactly the referenced final file remains.
    assert statuses == [HTTPStatus.OK, HTTPStatus.OK]
    assert store.resolve(relative).read_bytes() == b"x" * 5
    assert not staged.trash_path.exists()


async def test_startup_fails_closed_on_symlinked_final_entry(tmp_path: Path) -> None:
    # Given: an unreferenced member entry is a symlink to an outside file.
    active_settings = settings(tmp_path)
    store = LocalPhotoStore(active_settings)
    member_dir = store.root / "7"
    member_dir.mkdir()
    outside = tmp_path / "outside.png"
    _ = outside.write_bytes(b"outside")
    (member_dir / "linked.png").symlink_to(outside)

    # When/Then: startup refuses the storage tree without touching outside bytes.
    with pytest.raises(StoragePathError):
        _ = await _start_app(active_settings)
    assert outside.read_bytes() == b"outside"


async def test_startup_fails_closed_when_referenced_file_is_missing(
    tmp_path: Path,
) -> None:
    # Given: metadata references a file absent from both final storage and trash.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    _photo_id, relative = insert_photo(active_settings, user_id, size_bytes=5)
    store = LocalPhotoStore(active_settings)
    store.resolve(relative).unlink()

    # When/Then: startup refuses to serve a permanently inconsistent row.
    with pytest.raises(StoragePathError):
        _ = await _start_app(active_settings)


async def test_startup_fails_closed_on_invalid_upload_lease_expiration(
    tmp_path: Path,
) -> None:
    # Given: durable upload state contains a malformed expiration timestamp.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    with contextlib.closing(connect(active_settings)) as connection, connection:
        _ = connection.execute(
            "INSERT INTO upload_leases VALUES (?, ?, ?, ?, ?)",
            ("broken", user_id, 1, "2026-07-14T00:00:00+00:00", "zzzz"),
        )

    # When/Then: startup exposes the durable corruption instead of masking it as 503.
    with pytest.raises(ConfigurationError, match="invalid active upload lease"):
        _ = await _start_app(active_settings)


async def test_lifespan_rechecks_crashed_upload_after_lease_expiration(
    tmp_path: Path,
) -> None:
    # Given: a crashed upload left unreferenced bytes and a one-second lease.
    active_settings = settings(tmp_path, upload_lease_ttl_seconds=1)
    user_id = insert_user(active_settings)
    active_admission = admission(
        active_settings,
        lease_id="crashed",
        clock=lambda: dt.datetime.now(dt.UTC),
    )
    _lease = active_admission.acquire(user_id, 7)
    store = LocalPhotoStore(active_settings, name_factory=lambda: "crashed")
    relative = store.save(user_id, ".png", b"crashed")
    app = create_app(settings=active_settings)

    # When: the application remains live beyond the abandoned lease expiration.
    async with app.router.lifespan_context(app):
        assert (store.root / relative).exists()
        await anyio.sleep(1.2)

    # Then: the scheduled reconciliation removes the crash orphan without restart.
    assert not (store.root / relative).exists()
