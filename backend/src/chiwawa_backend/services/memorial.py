from datetime import UTC, datetime

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
from chiwawa_backend.state import AppState


def upload_photo(
    state: AppState,
    trip_id: str,
    payload: MemorialPhotoUploadRequest,
) -> MemorialPhotoRead:
    _ = require_trip(state, trip_id)
    photo = MemorialPhotoRead(
        id=state.next_id("photo"),
        trip_id=trip_id,
        file_name=payload.file_name,
        taken_at=payload.taken_at,
        latitude=payload.latitude,
        longitude=payload.longitude,
        memo=payload.memo,
    )
    state.photos[photo.id] = photo
    return photo


def list_photos(state: AppState, trip_id: str) -> MemorialPhotoListResponse:
    _ = require_trip(state, trip_id)
    items = [photo for photo in state.photos.values() if photo.trip_id == trip_id]
    return MemorialPhotoListResponse(trip_id=trip_id, items=items)


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
        timeline = [_photo_line(photo) for photo in photos]
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


def get_memorial(state: AppState, trip_id: str) -> MemorialRecordRead:
    return require_memorial(state, trip_id)


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


def _photo_line(photo: MemorialPhotoRead) -> str:
    taken_at = photo.taken_at or datetime.min.replace(tzinfo=UTC)
    return f"{taken_at.isoformat()} {photo.file_name}"
