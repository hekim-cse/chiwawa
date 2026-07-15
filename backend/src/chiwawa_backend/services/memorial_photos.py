"""회원 단위 Memorial 사진 오케스트레이션."""

from __future__ import annotations

import contextlib
import datetime as dt
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from chiwawa_backend.config import Settings, get_settings
from chiwawa_backend.errors import (
    AuthenticationError,
    ConfigurationError,
    DomainValidationError,
    NotFoundError,
    UnsupportedMediaTypeError,
)
from chiwawa_backend.schemas.memorial import (
    MemorialCalendarDay,
    MemorialCalendarResponse,
    MemorialDayResponse,
    MemorialPhotoItem,
    MemorialPhotoPatchRequest,
    MemorialTimelineEntry,
)
from chiwawa_backend.services.coordinates import (
    complete_coordinate_pair,
    require_coordinate_pair,
)
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.exif import InvalidImageError, inspect_image
from chiwawa_backend.services.geocode import reverse_geocode
from chiwawa_backend.services.local_photo_store import LocalPhotoStore
from chiwawa_backend.services.memorial_photo_commit import insert_photo_with_lease
from chiwawa_backend.services.memorial_photo_lifecycle import (
    delete_photo as delete_photo_lifecycle,
)
from chiwawa_backend.services.memorial_photo_repository import (
    NewPhotoRecord,
    day_photos,
    item_from_record,
    month_counts,
    normalize_storage,
    require_photo,
)
from chiwawa_backend.services.memorial_photo_updates import (
    update_photo as update_photo_metadata,
)
from chiwawa_backend.services.photo_times import current_photo_time
from chiwawa_backend.services.upload_admission import UploadAdmission

if TYPE_CHECKING:
    from collections.abc import Callable

    from chiwawa_backend.services.upload_admission import UploadLease

INVALID_IMAGE_DETAIL: Final = "uploaded file is not a valid image"
UNKNOWN_USER_DETAIL: Final = "unknown user"
MAX_FILE_NAME_CHARS: Final = 255
MAX_MEMO_CHARS: Final = 2000


@dataclass(frozen=True, slots=True)
class PhotoUpload:
    file_name: str
    content_type: str
    data: bytes
    taken_at: dt.datetime | None
    latitude: float | None
    longitude: float | None
    memo: str | None


def save_photo(
    user_id: int,
    upload: PhotoUpload,
    *,
    settings: Settings | None = None,
    store: LocalPhotoStore | None = None,
    admission: UploadAdmission | None = None,
) -> MemorialPhotoItem:
    if settings is None:
        with contextlib.closing(connect()):
            pass
    active_settings = settings or get_settings()
    active_store = store or LocalPhotoStore(active_settings)
    active_admission = admission or UploadAdmission(
        active_settings,
        store=active_store,
    )
    _validate_upload_metadata(upload)
    require_coordinate_pair(upload.latitude, upload.longitude)
    try:
        lease = active_admission.acquire(user_id, len(upload.data))
    except sqlite3.IntegrityError as error:
        raise AuthenticationError(UNKNOWN_USER_DETAIL) from error
    try:
        with active_admission.heartbeat(lease) as heartbeat:
            try:
                inspected = inspect_image(
                    upload.data,
                    max_dimension=active_settings.max_image_dimension,
                    max_pixels=active_settings.max_image_pixels,
                )
            except InvalidImageError as error:
                raise UnsupportedMediaTypeError(INVALID_IMAGE_DETAIL) from error
            exif = inspected.exif
            taken_at = upload.taken_at or exif.taken_at or current_photo_time()
            latitude, longitude = (
                (upload.latitude, upload.longitude)
                if upload.latitude is not None
                else complete_coordinate_pair(exif.latitude, exif.longitude)
            )
            require_coordinate_pair(latitude, longitude)
            address = _resolve_address(latitude, longitude)
            heartbeat.ensure_active()
            stored = active_store.save(user_id, inspected.suffix, upload.data)
            photo = NewPhotoRecord(
                user_id=user_id,
                file_name=upload.file_name,
                stored_path=stored.as_posix(),
                content_type=inspected.content_type,
                taken_at=taken_at,
                latitude=latitude,
                longitude=longitude,
                address=address,
                memo=upload.memo,
                created_at=_now_utc(),
                size_bytes=len(upload.data),
            )
            try:
                heartbeat.ensure_active()
                photo_id = _insert_photo_row(
                    active_settings,
                    photo,
                    lease,
                    active_admission.active_at,
                )
            except sqlite3.IntegrityError as error:
                with contextlib.suppress(OSError):
                    active_store.discard(stored)
                raise AuthenticationError(UNKNOWN_USER_DETAIL) from error
            except (ConfigurationError, OSError, sqlite3.Error):
                with contextlib.suppress(OSError):
                    active_store.discard(stored)
                raise
            return get_photo(user_id, photo_id, settings=active_settings)
    finally:
        with contextlib.suppress(ConfigurationError, OSError, sqlite3.Error):
            active_admission.release(lease)


def month_calendar(
    user_id: int,
    year: int,
    month: int,
    *,
    settings: Settings | None = None,
) -> MemorialCalendarResponse:
    active_settings = settings or get_settings()
    month_prefix = f"{year:04d}-{month:02d}"
    days = [
        MemorialCalendarDay(day=day, photo_count=photo_count)
        for day, photo_count in month_counts(active_settings, user_id, month_prefix)
    ]
    return MemorialCalendarResponse(year=year, month=month, days=days)


def day_timeline(
    user_id: int,
    day: dt.date,
    *,
    settings: Settings | None = None,
) -> MemorialDayResponse:
    active_settings = settings or get_settings()
    items = [
        MemorialTimelineEntry(seq=seq, photo=item_from_record(photo))
        for seq, photo in enumerate(day_photos(active_settings, user_id, day))
    ]
    return MemorialDayResponse(day=day, items=items)


def get_photo(
    user_id: int,
    photo_id: int,
    *,
    settings: Settings | None = None,
) -> MemorialPhotoItem:
    active_settings = settings or get_settings()
    return item_from_record(require_photo(active_settings, user_id, photo_id))


def photo_file(
    user_id: int,
    photo_id: int,
    *,
    settings: Settings | None = None,
    store: LocalPhotoStore | None = None,
) -> tuple[bytes, str]:
    active_settings = settings or get_settings()
    active_store = store or LocalPhotoStore(active_settings)
    record = require_photo(active_settings, user_id, photo_id)
    try:
        relative = active_store.parse_user_stored_path(
            record.user_id,
            record.stored_path,
        )
        data = active_store.read(relative)
        size_bytes = len(data)
    except OSError as error:
        raise NotFoundError(
            entity="memorial_photo_file",
            entity_id=str(photo_id),
        ) from error
    _ = normalize_storage(
        active_settings,
        record,
        relative.as_posix(),
        size_bytes,
    )
    return data, record.content_type


def update_photo(
    user_id: int,
    photo_id: int,
    patch: MemorialPhotoPatchRequest,
    *,
    settings: Settings | None = None,
) -> MemorialPhotoItem:
    active_settings = settings or get_settings()
    return update_photo_metadata(
        user_id,
        photo_id,
        patch,
        active_settings,
    )


def delete_photo(
    user_id: int,
    photo_id: int,
    *,
    settings: Settings | None = None,
    store: LocalPhotoStore | None = None,
) -> None:
    active_settings = settings or get_settings()
    delete_photo_lifecycle(user_id, photo_id, active_settings, store)


def _resolve_address(latitude: float | None, longitude: float | None) -> str | None:
    if latitude is None or longitude is None:
        return None
    return reverse_geocode(latitude, longitude)


def _validate_upload_metadata(upload: PhotoUpload) -> None:
    if len(upload.file_name) > MAX_FILE_NAME_CHARS:
        message = "photo file name is too long"
        raise DomainValidationError(message)
    if upload.memo is not None and len(upload.memo) > MAX_MEMO_CHARS:
        message = "photo memo is too long"
        raise DomainValidationError(message)


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


def _insert_photo_row(
    settings: Settings,
    photo: NewPhotoRecord,
    lease: UploadLease,
    active_at: Callable[[], str],
) -> int:
    return insert_photo_with_lease(settings, photo, lease, active_at)
