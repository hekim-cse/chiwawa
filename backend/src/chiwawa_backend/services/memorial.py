from chiwawa_backend.schemas.memorial import (
    MemorialGenerateRequest,
    MemorialPhotoListResponse,
    MemorialPhotoRead,
    MemorialPhotoUploadRequest,
    MemorialRecordRead,
    MemorialUpdateRequest,
)
from chiwawa_backend.services.common import require_memorial, require_trip
from chiwawa_backend.services.schedule import list_schedule
from chiwawa_backend.state import AppState, synchronized


@synchronized
def upload_photo(
    state: AppState,
    trip_id: str,
    payload: MemorialPhotoUploadRequest,
) -> MemorialPhotoRead:
    _ = require_trip(state, trip_id)
    if payload.device_photo_id is not None:
        existing = next(
            (
                photo
                for photo in state.photos.values()
                if photo.trip_id == trip_id
                and photo.device_photo_id == payload.device_photo_id
            ),
            None,
        )
        if existing is not None:
            return existing
    photo = MemorialPhotoRead(
        id=state.next_id("photo"),
        trip_id=trip_id,
        device_photo_id=payload.device_photo_id,
        file_name=payload.file_name,
        taken_at=payload.taken_at,
        latitude=payload.latitude,
        longitude=payload.longitude,
        memo=payload.memo,
    )
    state.photos[photo.id] = photo
    return photo


@synchronized
def list_photos(state: AppState, trip_id: str) -> MemorialPhotoListResponse:
    _ = require_trip(state, trip_id)
    items = [photo for photo in state.photos.values() if photo.trip_id == trip_id]
    return MemorialPhotoListResponse(trip_id=trip_id, items=items)


@synchronized
def generate_memorial(
    state: AppState,
    trip_id: str,
    payload: MemorialGenerateRequest,
) -> MemorialRecordRead:
    trip = require_trip(state, trip_id)
    photos = list_photos(state, trip_id).items
    schedule = list_schedule(state, trip_id)
    title = payload.title or f"{trip.title} memorial"
    timeline = [f"{item.date.isoformat()} {item.name}" for item in schedule.items]
    if not timeline:
        # 업로드 순서가 아니라 촬영 시각 순서로 타임라인을 만든다.
        # 촬영 시각이 없는 사진은 맨 뒤로 보낸다.
        timeline = [_photo_line(photo) for photo in sorted(photos, key=_photo_order)]
    summary = (
        f"{trip.city} trip with {len(schedule.items)} schedule items "
        f"and {len(photos)} photos."
    )
    memorial = MemorialRecordRead(
        id=state.next_id("memorial"),
        trip_id=trip_id,
        title=title,
        summary=summary,
        timeline=timeline,
        photo_count=len(photos),
    )
    state.memorials[trip_id] = memorial
    return memorial


@synchronized
def get_memorial(state: AppState, trip_id: str) -> MemorialRecordRead:
    return require_memorial(state, trip_id)


@synchronized
def update_memorial(
    state: AppState,
    trip_id: str,
    payload: MemorialUpdateRequest,
) -> MemorialRecordRead:
    memorial = require_memorial(state, trip_id)
    updated = MemorialRecordRead(
        id=memorial.id,
        trip_id=memorial.trip_id,
        title=payload.title or memorial.title,
        summary=payload.summary or memorial.summary,
        timeline=memorial.timeline,
        photo_count=memorial.photo_count,
    )
    state.memorials[trip_id] = updated
    return updated


def _photo_order(photo: MemorialPhotoRead) -> tuple[int, float]:
    # naive/aware datetime이 섞여도 비교할 수 있도록 timestamp로 정렬한다.
    if photo.taken_at is None:
        return (1, 0.0)
    return (0, photo.taken_at.timestamp())


def _photo_line(photo: MemorialPhotoRead) -> str:
    if photo.taken_at is None:
        return photo.file_name
    return f"{photo.taken_at.isoformat()} {photo.file_name}"
