from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

from ai.image_search.domain.search_schemas import (
    ImageSearchRequest,
    ImageSearchResult,
)
from ai.image_search.services.image_loader import ImageLoadError
from fastapi.concurrency import run_in_threadpool

from chiwawa_backend.errors import DomainValidationError, NotFoundError
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
from chiwawa_backend.state import AppState, synchronized

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

PHOTO_SEARCH_MAX_CANDIDATES = 5


class PhotoPlaceRecognizer(Protocol):
    def search(
        self,
        request: ImageSearchRequest,
    ) -> ImageSearchResult | Awaitable[ImageSearchResult]: ...


@dataclass(frozen=True, slots=True)
class PhotoPlaceSearchContext:
    trip_id: str
    payload: PhotoPlaceSearchRequest
    recognizer: PhotoPlaceRecognizer


async def search_photo_places(
    state: AppState,
    context: PhotoPlaceSearchContext,
) -> PhotoPlaceSearchResponse:
    with state.lock:
        trip = require_trip(state, context.trip_id)

    request = ImageSearchRequest(
        image_url=context.payload.image_url,
        note=context.payload.note,
        latitude=context.payload.latitude,
        longitude=context.payload.longitude,
        city=trip.city,
        country=trip.country,
        max_candidates=PHOTO_SEARCH_MAX_CANDIDATES,
    )
    try:
        result = await _search_recognizer(context.recognizer, request)
    except ImageLoadError as error:
        raise DomainValidationError(str(error)) from error

    with state.lock:
        trip = require_trip(state, context.trip_id)
        candidates = [
            PhotoPlaceCandidateRead(
                id=state.next_id("candidate"),
                name=candidate.name,
                city=candidate.city or trip.city,
                country=candidate.country or trip.country,
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                confidence=candidate.confidence,
                reason=candidate.reason,
            )
            for candidate in result.candidates
        ]
        search = PhotoPlaceSearchResponse(
            id=state.next_id("photo_search"),
            trip_id=context.trip_id,
            candidates=candidates,
        )
        state.photo_searches[search.id] = search
    return search


async def _search_recognizer(
    recognizer: PhotoPlaceRecognizer,
    request: ImageSearchRequest,
) -> ImageSearchResult:
    search = recognizer.search
    if inspect.iscoroutinefunction(search):
        async_search = cast(
            "Callable[[ImageSearchRequest], Awaitable[ImageSearchResult]]",
            search,
        )
        return await async_search(request)
    sync_search = cast(
        "Callable[[ImageSearchRequest], ImageSearchResult]",
        search,
    )
    return await run_in_threadpool(sync_search, request)


@synchronized
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
    existing = state.confirmed_photo_places.get(candidate.id)
    if existing is not None:
        current_place = state.wanted_places.get(existing.wanted_place.id)
        # wanted place가 삭제됐다면 아래에서 새로 만들고,
        # 남아 있다면 확정 당시 스냅샷 대신 현재 상태로 응답을 재구성해
        # PATCH 이후에도 GET /wanted-places와 일치하도록 한다.
        if current_place is not None:
            return ConfirmedPhotoPlaceRead(
                search_id=existing.search_id,
                candidate=existing.candidate,
                wanted_place=current_place,
            )
    trip = require_trip(state, trip_id)
    wanted_place = create_wanted_place(
        state,
        trip_id,
        WantedPlaceCreateRequest(
            name=candidate.name,
            city=candidate.city or trip.city,
            country=candidate.country or trip.country,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
            priority=5,
            notes=candidate.reason,
        ),
        source=PlaceSource.PHOTO,
    )
    confirmation = ConfirmedPhotoPlaceRead(
        search_id=search_id,
        candidate=candidate,
        wanted_place=wanted_place,
    )
    state.confirmed_photo_places[candidate.id] = confirmation
    return confirmation
