# 일반 장소 검색 Use Case와 외부 Provider Port
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from chiwawa_backend.schemas.place_search import PlaceSearchCandidateRead


class PlaceSearchProvider(Protocol):
    async def search(
        self,
        *,
        query: str,
        city_bias: str | None,
    ) -> tuple[PlaceSearchCandidateRead, ...]: ...
