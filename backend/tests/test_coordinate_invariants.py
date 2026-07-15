from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

import pytest

from chiwawa_backend.errors import DomainValidationError
from chiwawa_backend.schemas.base import TravelStyle
from chiwawa_backend.schemas.memorial import (
    MemorialPhotoPatchRequest,
    MemorialPhotoUploadRequest,
)
from chiwawa_backend.schemas.places import (
    PhotoPlaceSearchRequest,
    WantedPlaceCreateRequest,
    WantedPlaceUpdateRequest,
)
from chiwawa_backend.schemas.trips import TripRead
from chiwawa_backend.services import memorial, memorial_photos, wanted_places
from chiwawa_backend.services.exif import ImageInspection, PhotoExif
from chiwawa_backend.services.memorial_photos import PhotoUpload
from chiwawa_backend.state import AppState
from tests.memorial_test_support import insert_photo, insert_user, png, settings

if TYPE_CHECKING:
    from pathlib import Path


def _stub_inspection(
    monkeypatch: pytest.MonkeyPatch,
    inspection: ImageInspection,
) -> None:
    def inspect(
        _data: bytes,
        *,
        max_dimension: int,
        max_pixels: int,
    ) -> ImageInspection:
        _ = max_dimension, max_pixels
        return inspection

    monkeypatch.setattr(memorial_photos, "inspect_image", inspect)


def _state() -> AppState:
    state = AppState()
    trip = TripRead(
        id="trip_coordinates",
        title="Tokyo",
        city="Tokyo",
        country="Japan",
        start_date=dt.date(2026, 7, 10),
        end_date=dt.date(2026, 7, 12),
        travelers=1,
        interests=[],
        travel_style=TravelStyle.BALANCED,
    )
    state.trips[trip.id] = trip
    return state


def test_services_reject_constructed_partial_coordinate_models(tmp_path: Path) -> None:
    state = _state()
    trip_id = next(iter(state.trips))
    wanted = WantedPlaceCreateRequest.model_construct(name="A", latitude=35.0)
    legacy = MemorialPhotoUploadRequest.model_construct(
        file_name="a.jpg",
        latitude=35.0,
    )
    with pytest.raises(DomainValidationError):
        _ = wanted_places.create_wanted_place(state, trip_id, wanted)
    with pytest.raises(DomainValidationError):
        _ = memorial.upload_photo(state, trip_id, legacy)
    existing = wanted_places.create_wanted_place(
        state,
        trip_id,
        WantedPlaceCreateRequest(
            name="Existing",
            latitude=35.0,
            longitude=139.0,
        ),
    )
    partial_update = WantedPlaceUpdateRequest.model_construct(latitude=36.0)
    with pytest.raises(DomainValidationError):
        _ = wanted_places.update_wanted_place(
            state,
            trip_id,
            existing.id,
            partial_update,
        )

    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    photo_id, _relative = insert_photo(active_settings, user_id, size_bytes=4)
    patch = MemorialPhotoPatchRequest.model_construct(latitude=35.0)
    with pytest.raises(DomainValidationError):
        _ = memorial_photos.update_photo(
            user_id,
            photo_id,
            patch,
            settings=active_settings,
        )


def test_photo_place_search_rejects_partial_coordinates() -> None:
    with pytest.raises(ValueError, match="must be provided together"):
        _ = PhotoPlaceSearchRequest(latitude=35.0)


def test_partial_exif_coordinates_are_not_persisted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    inspection = ImageInspection(
        content_type="image/png",
        suffix=".png",
        exif=PhotoExif(taken_at=None, latitude=35.0, longitude=None),
    )
    _stub_inspection(monkeypatch, inspection)
    saved = memorial_photos.save_photo(
        user_id,
        PhotoUpload(
            file_name="partial.png",
            content_type="image/png",
            data=png(),
            taken_at=None,
            latitude=None,
            longitude=None,
            memo=None,
        ),
        settings=active_settings,
    )
    assert (saved.latitude, saved.longitude) == (None, None)


def test_out_of_range_exif_coordinates_are_not_persisted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    active_settings = settings(tmp_path)
    user_id = insert_user(active_settings)
    inspection = ImageInspection(
        content_type="image/png",
        suffix=".png",
        exif=PhotoExif(taken_at=None, latitude=999.0, longitude=999.0),
    )
    _stub_inspection(monkeypatch, inspection)
    saved = memorial_photos.save_photo(
        user_id,
        PhotoUpload(
            file_name="invalid.png",
            content_type="image/png",
            data=png(),
            taken_at=None,
            latitude=None,
            longitude=None,
            memo=None,
        ),
        settings=active_settings,
    )
    assert (saved.latitude, saved.longitude) == (None, None)
