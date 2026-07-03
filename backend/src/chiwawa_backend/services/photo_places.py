from chiwawa_backend.errors import NotFoundError
from chiwawa_backend.schemas.base import PlaceSource
from chiwawa_backend.schemas.places import (
    ConfirmedPhotoPlaceRead,
    PhotoPlaceCandidateRead,
    PhotoPlaceConfirmRequest,
    PhotoPlaceSearchRequest,
    PhotoPlaceSearchResponse,
    WantedPlaceCreateRequest,
)
from chiwawa_backend.services.common import require_photo_search, require_trip
from chiwawa_backend.services.wanted_places import create_wanted_place
from chiwawa_backend.state import AppState


def search_photo_places(
    state: AppState,
    trip_id: str,
    payload: PhotoPlaceSearchRequest,
) -> PhotoPlaceSearchResponse:
    trip = require_trip(state, trip_id)
    city = trip.city
    note = payload.note or "uploaded travel photo"
    candidates = [
        PhotoPlaceCandidateRead(
            id=state.next_id("candidate"),
            name=f"{city} landmark viewpoint",
            city=city,
            country=trip.country,
            latitude=35.6586,
            longitude=139.7454,
            confidence=0.91,
            reason=f"Best match for {note}",
        ),
        PhotoPlaceCandidateRead(
            id=state.next_id("candidate"),
            name=f"{city} local photo spot",
            city=city,
            country=trip.country,
            latitude=35.6595,
            longitude=139.7005,
            confidence=0.84,
            reason="Similar skyline, street texture, and travel context",
        ),
        PhotoPlaceCandidateRead(
            id=state.next_id("candidate"),
            name=f"{city} evening walk area",
            city=city,
            country=trip.country,
            latitude=35.6716,
            longitude=139.765,
            confidence=0.76,
            reason="Useful nearby alternative for route planning",
        ),
    ]
    search = PhotoPlaceSearchResponse(
        id=state.next_id("photo_search"),
        trip_id=trip_id,
        candidates=candidates,
    )
    state.photo_searches[search.id] = search
    return search


def confirm_photo_place(
    state: AppState,
    trip_id: str,
    search_id: str,
    payload: PhotoPlaceConfirmRequest,
) -> ConfirmedPhotoPlaceRead:
    search = require_photo_search(state, trip_id, search_id)
    candidate = next(
        (item for item in search.candidates if item.id == payload.candidate_id),
        None,
    )
    if candidate is None:
        raise NotFoundError(entity="photo_candidate", entity_id=payload.candidate_id)
    wanted_place = create_wanted_place(
        state=state,
        trip_id=trip_id,
        payload=WantedPlaceCreateRequest(
            name=candidate.name,
            city=candidate.city,
            country=candidate.country,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
            priority=5,
            notes=candidate.reason,
        ),
        source=PlaceSource.PHOTO,
    )
    return ConfirmedPhotoPlaceRead(
        search_id=search_id,
        candidate=candidate,
        wanted_place=wanted_place,
    )
