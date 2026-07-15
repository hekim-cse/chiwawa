from __future__ import annotations

import datetime as dt

from chiwawa_backend.schemas.base import PlaceSource, TravelStyle
from chiwawa_backend.schemas.memorial import (
    MemorialRecordRead,
    MemorialUpdateRequest,
)
from chiwawa_backend.schemas.places import (
    WantedPlaceRead,
    WantedPlaceUpdateRequest,
)
from chiwawa_backend.schemas.schedule import (
    ScheduleItemRead,
    ScheduleItemUpdateRequest,
)
from chiwawa_backend.schemas.trips import TripRead, TripUpdateRequest
from chiwawa_backend.services import (
    memorial,
    schedule,
    trips,
    wanted_places,
)
from chiwawa_backend.state import AppState


def _trip() -> TripRead:
    return TripRead(
        id="trip_patch",
        title="Tokyo trip",
        city="Tokyo",
        country="Japan",
        start_date=dt.date(2026, 7, 10),
        end_date=dt.date(2026, 7, 12),
        travelers=2,
        interests=["food"],
        travel_style=TravelStyle.BALANCED,
    )


def test_trip_and_memorial_patch_omit_preserves_and_replacement_updates() -> None:
    # Given: a trip and generated memorial with required text fields.
    state = AppState()
    original_trip = _trip()
    state.trips[original_trip.id] = original_trip
    original_memorial = MemorialRecordRead(
        id="memorial_1",
        trip_id=original_trip.id,
        title="Original",
        summary="Original summary",
        timeline=[],
        photo_count=0,
    )
    state.memorials[original_trip.id] = original_memorial

    # When: empty PATCHes are followed by explicit replacements.
    preserved_trip = trips.update_trip(state, original_trip.id, TripUpdateRequest())
    preserved_memorial = memorial.update_memorial(
        state,
        original_trip.id,
        MemorialUpdateRequest(),
    )
    updated_trip = trips.update_trip(
        state,
        original_trip.id,
        TripUpdateRequest(city="Kyoto"),
    )
    updated_memorial = memorial.update_memorial(
        state,
        original_trip.id,
        MemorialUpdateRequest(summary="Replacement"),
    )

    # Then: omission preserves and supplied values replace the prior values.
    assert preserved_trip == original_trip
    assert preserved_memorial == original_memorial
    assert updated_trip.city == "Kyoto"
    assert updated_memorial.summary == "Replacement"


def test_wanted_and_schedule_patch_can_clear_nullable_fields() -> None:
    # Given: wanted and schedule records with nullable fields populated.
    state = AppState()
    trip = _trip()
    state.trips[trip.id] = trip
    place = WantedPlaceRead(
        id="place_1",
        trip_id=trip.id,
        name="Tower",
        city="Tokyo",
        country="Japan",
        latitude=35.0,
        longitude=139.0,
        priority=5,
        notes="Sunset",
        source=PlaceSource.MANUAL,
    )
    state.wanted_places[place.id] = place
    item = ScheduleItemRead(
        id="schedule_1",
        trip_id=trip.id,
        name="Tower visit",
        date=trip.start_date,
        start_time=dt.time(10),
        end_time=dt.time(11),
        place_id=place.id,
        notes="Reserved",
        source=PlaceSource.MANUAL,
    )
    state.schedule_items[item.id] = item

    # When: nullable coordinates, notes, and place references are explicitly cleared.
    assert (
        wanted_places.update_wanted_place(
            state,
            trip.id,
            place.id,
            WantedPlaceUpdateRequest(),
        )
        == place
    )
    assert (
        schedule.update_schedule_item(
            state,
            trip.id,
            item.id,
            ScheduleItemUpdateRequest(),
        )
        == item
    )
    cleared_place = wanted_places.update_wanted_place(
        state,
        trip.id,
        place.id,
        WantedPlaceUpdateRequest(
            latitude=None,
            longitude=None,
            notes=None,
        ),
    )
    cleared_item = schedule.update_schedule_item(
        state,
        trip.id,
        item.id,
        ScheduleItemUpdateRequest(place_id=None, notes=None),
    )

    # Then: explicit null clears while required snapshot fields remain intact.
    assert (cleared_place.latitude, cleared_place.longitude, cleared_place.notes) == (
        None,
        None,
        None,
    )
    assert (cleared_item.place_id, cleared_item.notes, cleared_item.name) == (
        None,
        None,
        item.name,
    )
    renamed_place = wanted_places.update_wanted_place(
        state,
        trip.id,
        place.id,
        WantedPlaceUpdateRequest(name="Replacement place"),
    )
    renamed_item = schedule.update_schedule_item(
        state,
        trip.id,
        item.id,
        ScheduleItemUpdateRequest(name="Replacement item"),
    )
    assert renamed_place.name == "Replacement place"
    assert renamed_item.name == "Replacement item"
