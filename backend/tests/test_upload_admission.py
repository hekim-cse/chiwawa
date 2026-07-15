from __future__ import annotations

import contextlib
import datetime as dt
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import pytest

from chiwawa_backend.errors import (
    ApplicationError,
    InsufficientStorageError,
    PayloadTooLargeError,
    RateLimitError,
)
from chiwawa_backend.services import memorial_photos
from tests.memorial_test_support import (
    NOW,
    admission,
    insert_photo,
    insert_user,
    settings,
)

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.services.upload_admission import UploadAdmission

UPLOAD_ERROR_STATUSES: dict[type[ApplicationError], HTTPStatus] = {
    PayloadTooLargeError: HTTPStatus.CONTENT_TOO_LARGE,
    RateLimitError: HTTPStatus.TOO_MANY_REQUESTS,
    InsufficientStorageError: HTTPStatus.INSUFFICIENT_STORAGE,
}


def _assert_application_error(
    gate: UploadAdmission,
    user_id: int,
    size_bytes: int,
    expected: HTTPStatus,
) -> ApplicationError:
    with pytest.raises(ApplicationError) as captured:
        _ = gate.acquire(user_id, size_bytes)
    assert UPLOAD_ERROR_STATUSES[type(captured.value)] == expected
    return captured.value


def test_admission_enforces_file_count_and_total_byte_quotas(tmp_path: Path) -> None:
    # Given: strict file/count/byte settings and one persisted photo.
    active_settings = settings(
        tmp_path,
        max_photo_bytes=20,
        max_photos_per_user=1,
        max_photo_bytes_per_user=15,
    )
    user_id = insert_user(active_settings)
    _, _relative = insert_photo(active_settings, user_id, size_bytes=10)
    gate = admission(active_settings, lease_id="quota")

    # When/Then: each quota class rejects with 413 before a lease is created.
    _ = _assert_application_error(gate, user_id, 21, HTTPStatus.CONTENT_TOO_LARGE)
    _ = _assert_application_error(gate, user_id, 1, HTTPStatus.CONTENT_TOO_LARGE)
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        _ = connection.execute(
            "DELETE FROM memorial_photos WHERE user_id = ?", (user_id,)
        )
        connection.commit()
    _ = _assert_application_error(gate, user_id, 16, HTTPStatus.CONTENT_TOO_LARGE)


def test_shared_leases_enforce_user_and_global_concurrency(tmp_path: Path) -> None:
    # Given: separate global and per-user concurrency policies.
    active_settings = settings(
        tmp_path,
        max_concurrent_uploads=1,
        max_concurrent_uploads_per_user=1,
    )
    first_user = insert_user(active_settings, "first")
    second_user = insert_user(active_settings, "second")
    first = admission(active_settings, lease_id="first-lease")
    second = admission(active_settings, lease_id="second-lease")
    lease = first.acquire(first_user, 5)

    # When/Then: a distinct user is rejected by the global shared limit.
    global_error = _assert_application_error(
        second, second_user, 5, HTTPStatus.TOO_MANY_REQUESTS
    )
    assert global_error.headers == {"Retry-After": "60"}
    first.release(lease)

    user_settings = settings(
        tmp_path / "user-limit",
        max_concurrent_uploads=2,
        max_concurrent_uploads_per_user=1,
    )
    same_user = insert_user(user_settings)
    user_first = admission(user_settings, lease_id="user-first")
    user_second = admission(user_settings, lease_id="user-second")
    _ = user_first.acquire(same_user, 5)
    user_error = _assert_application_error(
        user_second,
        same_user,
        5,
        HTTPStatus.TOO_MANY_REQUESTS,
    )
    assert user_error.headers == {"Retry-After": "60"}


def test_two_concurrent_instances_cannot_overshoot_global_limit(tmp_path: Path) -> None:
    # Given: two workers contend for the only shared upload slot.
    active_settings = settings(tmp_path, max_concurrent_uploads=1)
    users = (
        insert_user(active_settings, "thread-a"),
        insert_user(active_settings, "thread-b"),
    )
    gates = (
        admission(active_settings, lease_id="thread-lease-a"),
        admission(active_settings, lease_id="thread-lease-b"),
    )

    def acquire(index: int) -> int:
        try:
            _ = gates[index].acquire(users[index], 5)
        except ApplicationError as error:
            return UPLOAD_ERROR_STATUSES[type(error)]
        return HTTPStatus.OK

    # When: both attempt acquisition from distinct threads.
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(acquire, (0, 1)))

    # Then: SQLite serialization admits exactly one lease.
    assert sorted(statuses) == [HTTPStatus.OK, HTTPStatus.TOO_MANY_REQUESTS]


def test_rate_attempts_and_disk_watermark_are_shared_and_deterministic(
    tmp_path: Path,
) -> None:
    # Given: one hourly attempt and a disk probe unable to retain requested bytes.
    rate_settings = settings(tmp_path, max_uploads_per_user_per_hour=1)
    user_id = insert_user(rate_settings)
    first = admission(rate_settings, lease_id="rate-a")
    first.release(first.acquire(user_id, 5))

    # When/Then: another instance rejects rate and records the attempt.
    rate_error = _assert_application_error(
        admission(rate_settings, lease_id="rate-b"),
        user_id,
        5,
        HTTPStatus.TOO_MANY_REQUESTS,
    )
    assert rate_error.headers is not None
    assert int(rate_error.headers["Retry-After"]) > 0
    with contextlib.closing(
        sqlite3.connect(rate_settings.auth_db_path())
    ) as connection:
        event_count = cast(
            "tuple[int] | None",
            connection.execute("SELECT COUNT(*) FROM upload_events").fetchone(),
        )
    assert event_count == (2,)

    disk_settings = settings(tmp_path / "disk")
    disk_user = insert_user(disk_settings)
    _ = _assert_application_error(
        admission(disk_settings, lease_id="disk", free_bytes=5),
        disk_user,
        5,
        HTTPStatus.INSUFFICIENT_STORAGE,
    )


def test_disk_watermark_includes_other_users_active_reservations(
    tmp_path: Path,
) -> None:
    # Given: one active four-byte lease leaves only two bytes above the watermark.
    active_settings = settings(
        tmp_path,
        min_free_disk_bytes=5,
        max_concurrent_uploads=2,
    )
    first_user = insert_user(active_settings, "disk-first")
    second_user = insert_user(active_settings, "disk-second")
    first = admission(active_settings, lease_id="disk-first", free_bytes=11)
    second = admission(active_settings, lease_id="disk-second", free_bytes=11)
    _ = first.acquire(first_user, 4)

    # When: another process-equivalent instance reserves four more bytes.
    error = _assert_application_error(
        second,
        second_user,
        4,
        HTTPStatus.INSUFFICIENT_STORAGE,
    )

    # Then: shared reservations are projected before the disk watermark decision.
    assert error.detail == "insufficient local photo storage"


def test_expired_lease_and_deleted_row_release_reservations(tmp_path: Path) -> None:
    # Given: an expired lease and a persisted row consuming the count quota.
    active_settings = settings(
        tmp_path,
        max_photos_per_user=1,
        max_photo_bytes_per_user=5,
    )
    user_id = insert_user(active_settings)
    photo_id, _relative = insert_photo(active_settings, user_id, size_bytes=5)
    with contextlib.closing(
        sqlite3.connect(active_settings.auth_db_path())
    ) as connection:
        _ = connection.execute(
            "INSERT INTO upload_leases VALUES (?, ?, ?, ?, ?)",
            (
                "expired",
                user_id,
                10,
                (NOW - dt.timedelta(minutes=2)).isoformat(),
                (NOW - dt.timedelta(minutes=1)).isoformat(),
            ),
        )
        connection.commit()
    gate = admission(active_settings, lease_id="fresh")

    # When: the service deletes the persisted photo and admission purges the old lease.
    memorial_photos.delete_photo(user_id, photo_id, settings=active_settings)
    lease = gate.acquire(user_id, 5)

    # Then: both count and byte reservation capacity are released.
    gate.release(lease)
    assert gate.acquire(user_id, 5).lease_id == "fresh"


def test_active_leases_count_toward_photo_and_byte_quotas(tmp_path: Path) -> None:
    # Given: one active reservation fills both per-user quotas.
    active_settings = settings(
        tmp_path,
        max_photos_per_user=1,
        max_photo_bytes_per_user=5,
        max_concurrent_uploads_per_user=2,
    )
    user_id = insert_user(active_settings)
    first = admission(active_settings, lease_id="reserved")
    second = admission(active_settings, lease_id="blocked")
    _ = first.acquire(user_id, 5)

    # When/Then: another worker cannot reserve beyond count or byte capacity.
    _ = _assert_application_error(second, user_id, 1, HTTPStatus.CONTENT_TOO_LARGE)

    byte_settings = settings(
        tmp_path / "bytes",
        max_photos_per_user=2,
        max_photo_bytes_per_user=5,
        max_concurrent_uploads_per_user=2,
    )
    byte_user = insert_user(byte_settings)
    byte_first = admission(byte_settings, lease_id="byte-reserved")
    byte_second = admission(byte_settings, lease_id="byte-blocked")
    _ = byte_first.acquire(byte_user, 5)
    byte_error = _assert_application_error(
        byte_second,
        byte_user,
        1,
        HTTPStatus.CONTENT_TOO_LARGE,
    )
    assert byte_error.detail == "photo byte quota exceeded"


def test_two_instances_cannot_overshoot_per_user_photo_quota(tmp_path: Path) -> None:
    # Given: per-user count permits one active or persisted photo.
    active_settings = settings(
        tmp_path,
        max_photos_per_user=1,
        max_concurrent_uploads=2,
        max_concurrent_uploads_per_user=2,
    )
    user_id = insert_user(active_settings)
    gates = (
        admission(active_settings, lease_id="quota-a"),
        admission(active_settings, lease_id="quota-b"),
    )

    def acquire(index: int) -> int:
        try:
            _ = gates[index].acquire(user_id, 1)
        except ApplicationError as error:
            return UPLOAD_ERROR_STATUSES[type(error)]
        return HTTPStatus.OK

    # When: two process-equivalent instances race for that quota.
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(acquire, (0, 1)))

    # Then: the shared lease reservation makes quota enforcement atomic.
    assert sorted(statuses) == [HTTPStatus.OK, HTTPStatus.CONTENT_TOO_LARGE]
