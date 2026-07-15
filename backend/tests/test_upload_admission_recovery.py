from __future__ import annotations

import contextlib
import datetime as dt
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import TYPE_CHECKING, cast

import pytest

from chiwawa_backend.errors import (
    ApplicationError,
    ConfigurationError,
    PayloadTooLargeError,
    RateLimitError,
)
from chiwawa_backend.services import memorial_photos
from chiwawa_backend.services.local_photo_store import LocalPhotoStore
from chiwawa_backend.services.memorial_photo_recovery import (
    reconcile_memorial_photos,
)
from chiwawa_backend.services.memorial_photos import PhotoUpload
from chiwawa_backend.services.upload_admission import UploadAdmission
from tests.memorial_test_support import (
    NOW,
    admission,
    insert_photo,
    insert_user,
    png,
    settings,
)

if TYPE_CHECKING:
    from pathlib import Path


def _assert_application_error(
    gate: UploadAdmission,
    user_id: int,
    size_bytes: int,
    expected: type[ApplicationError],
) -> ApplicationError:
    with pytest.raises(expected) as captured:
        _ = gate.acquire(user_id, size_bytes)
    return captured.value


def test_obeying_rate_retry_after_allows_next_attempt(tmp_path: Path) -> None:
    # Given: a success followed by one rejected attempt on a movable fake clock.
    active_settings = settings(tmp_path, max_uploads_per_user_per_hour=1)
    user_id = insert_user(active_settings)
    current = [NOW]
    first = admission(
        active_settings,
        lease_id="retry-first",
        clock=lambda: current[0],
    )
    first.release(first.acquire(user_id, 1))
    current[0] += dt.timedelta(minutes=1)
    rejected = admission(
        active_settings,
        lease_id="retry-rejected",
        clock=lambda: current[0],
    )
    error = _assert_application_error(
        rejected,
        user_id,
        1,
        RateLimitError,
    )
    assert error.headers is not None

    # When: the client advances by the exact advertised Retry-After.
    current[0] += dt.timedelta(seconds=int(error.headers["Retry-After"]))
    retry = admission(
        active_settings,
        lease_id="retry-success",
        clock=lambda: current[0],
    )

    # Then: the next acquisition is admitted without another retry cycle.
    assert retry.acquire(user_id, 1).lease_id == "retry-success"


def test_lease_id_collision_rolls_back_rate_event(tmp_path: Path) -> None:
    # Given: an active lease and a second instance generating the same identifier.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    first = admission(active_settings, lease_id="duplicate")
    second = admission(active_settings, lease_id="duplicate")
    _ = first.acquire(user_id, 1)

    # When: the second acquisition reaches its exclusive lease insert.
    with pytest.raises(ConfigurationError, match="lease id collision"):
        _ = second.acquire(user_id, 1)

    # Then: the failed internal collision does not consume a rate attempt.
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        event_count = cast(
            "tuple[int] | None",
            connection.execute("SELECT COUNT(*) FROM upload_events").fetchone(),
        )
        lease_count = cast(
            "tuple[int] | None",
            connection.execute("SELECT COUNT(*) FROM upload_leases").fetchone(),
        )
    assert event_count == (1,)
    assert lease_count == (1,)


def test_expired_lease_cannot_be_renewed(tmp_path: Path) -> None:
    # Given: a lease expires while its worker is unable to refresh it.
    active_settings = settings(tmp_path, upload_lease_ttl_seconds=1)
    user_id = insert_user(active_settings)
    current = [NOW]
    gate = admission(
        active_settings,
        lease_id="expired-refresh",
        clock=lambda: current[0],
    )
    lease = gate.acquire(user_id, 1)
    current[0] += dt.timedelta(seconds=2)

    # When/Then: renewal cannot resurrect the expired recovery fence.
    with pytest.raises(ConfigurationError, match="no longer active"):
        gate.renew(lease)


def test_admission_backfills_legacy_zero_size_before_quota_check(
    tmp_path: Path,
) -> None:
    # Given: a non-empty legacy file is recorded with the migration's zero default.
    active_settings = settings(tmp_path, max_photo_bytes_per_user=10)
    user_id = insert_user(active_settings)
    photo_id, _relative = insert_photo(active_settings, user_id, size_bytes=10)
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        _ = connection.execute(
            "UPDATE memorial_photos SET size_bytes = 0 WHERE id = ?",
            (photo_id,),
        )
        connection.commit()
    gate = admission(active_settings, lease_id="legacy")

    # When: another byte is requested against the shared per-user quota.
    error = _assert_application_error(gate, user_id, 1, PayloadTooLargeError)

    # Then: the real legacy file size is counted and persisted before rejection.
    assert error.detail == "photo byte quota exceeded"
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        stored_size = cast(
            "tuple[int] | None",
            connection.execute(
                "SELECT size_bytes FROM memorial_photos WHERE id = ?",
                (photo_id,),
            ).fetchone(),
        )
    assert stored_size == (10,)


def test_upload_heartbeat_prevents_recovery_from_deleting_inflight_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: a one-second lease and an upload paused after durable local save.
    active_settings = settings(tmp_path, upload_lease_ttl_seconds=1)
    user_id = insert_user(active_settings)
    store = LocalPhotoStore(active_settings, name_factory=lambda: "inflight")
    gate = UploadAdmission(active_settings, store=store)
    file_saved = Event()
    release_save = Event()
    original_save = store.save

    def delayed_save(user_id_arg: int, suffix: str, data: bytes) -> Path:
        relative = original_save(user_id_arg, suffix, data)
        file_saved.set()
        assert release_save.wait(timeout=3)
        return relative

    monkeypatch.setattr(store, "save", delayed_save)
    upload = PhotoUpload(
        file_name="inflight.png",
        content_type="image/png",
        data=png(),
        taken_at=None,
        latitude=None,
        longitude=None,
        memo=None,
    )

    # When: recovery runs after the original lease duration while upload is active.
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            memorial_photos.save_photo,
            user_id,
            upload,
            settings=active_settings,
            store=store,
            admission=gate,
        )
        assert file_saved.wait(timeout=2)
        time.sleep(1.2)
        active_until = reconcile_memorial_photos(active_settings)
        relative = store.parse_stored_path(f"{user_id}/inflight.png")
        assert active_until is not None
        assert (store.root / relative).exists()
        release_save.set()
        photo = future.result(timeout=3)

    # Then: both the committed row and its durable local file remain readable.
    assert photo.file_name == "inflight.png"
    assert store.resolve(relative).read_bytes() == upload.data
