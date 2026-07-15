from __future__ import annotations

import contextlib
import datetime as dt
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from chiwawa_backend.schemas.memorial import MemorialPhotoPatchRequest
from chiwawa_backend.services import (
    memorial_photo_repository,
    memorial_photo_updates,
    memorial_photos,
)
from chiwawa_backend.services.database import connect
from tests.memorial_test_support import insert_photo, insert_user, settings

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from chiwawa_backend.config import Settings


def test_member_photo_patch_clears_nullable_metadata(tmp_path: Path) -> None:
    # Given: a persisted member photo with GPS, address, and memo metadata.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    photo_id, _relative = insert_photo(active_settings, user_id, size_bytes=4)
    with contextlib.closing(connect(active_settings)) as connection, connection:
        _ = connection.execute(
            """
            UPDATE memorial_photos
            SET latitude = 35.0, longitude = 139.0,
                address = 'Tokyo', memo = 'Keep me'
            WHERE id = ?
            """,
            (photo_id,),
        )
    original = memorial_photos.get_photo(
        user_id,
        photo_id,
        settings=active_settings,
    )
    assert (
        memorial_photos.update_photo(
            user_id,
            photo_id,
            MemorialPhotoPatchRequest(),
            settings=active_settings,
        )
        == original
    )

    # When: the nullable fields are explicitly cleared together.
    updated = memorial_photos.update_photo(
        user_id,
        photo_id,
        MemorialPhotoPatchRequest(
            latitude=None,
            longitude=None,
            memo=None,
        ),
        settings=active_settings,
    )

    # Then: persisted metadata is null and the required timestamp is preserved.
    assert (updated.latitude, updated.longitude, updated.address, updated.memo) == (
        None,
        None,
        None,
        None,
    )
    assert updated.taken_at == dt.datetime(
        2026,
        7,
        14,
        10,
        tzinfo=dt.timezone(dt.timedelta(hours=9)),
    )
    replaced = memorial_photos.update_photo(
        user_id,
        photo_id,
        MemorialPhotoPatchRequest(memo="Replacement"),
        settings=active_settings,
    )
    assert replaced.memo == "Replacement"


def test_concurrent_photo_patches_preserve_independent_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: two PATCH requests read the same photo snapshot concurrently.
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    photo_id, _relative = insert_photo(active_settings, user_id, size_bytes=4)
    barrier = threading.Barrier(2)
    thread_state = threading.local()
    original_require_photo = memorial_photo_repository.require_photo

    def synchronized_require_photo(
        settings_arg: Settings,
        user_id_arg: int,
        photo_id_arg: int,
    ) -> memorial_photo_repository.PhotoRecord:
        record = original_require_photo(settings_arg, user_id_arg, photo_id_arg)
        if not getattr(thread_state, "has_waited", False):
            thread_state.has_waited = True
            _ = barrier.wait(timeout=2)
        return record

    monkeypatch.setattr(
        memorial_photo_updates,
        "require_photo",
        synchronized_require_photo,
    )
    new_taken_at = dt.datetime(2026, 7, 15, 12, tzinfo=dt.UTC)

    # When: each request changes a different field and both report success.
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(
                memorial_photo_updates.update_photo,
                user_id,
                photo_id,
                MemorialPhotoPatchRequest(memo="new memo"),
                active_settings,
            ),
            executor.submit(
                memorial_photo_updates.update_photo,
                user_id,
                photo_id,
                MemorialPhotoPatchRequest(taken_at=new_taken_at),
                active_settings,
            ),
        )
        _ = [future.result(timeout=3) for future in futures]

    # Then: the durable row contains both independent updates.
    updated = original_require_photo(active_settings, user_id, photo_id)
    assert updated.memo == "new memo"
    assert updated.taken_at == new_taken_at
