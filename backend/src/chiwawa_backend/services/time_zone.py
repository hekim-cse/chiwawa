# 출발지 좌표를 IANA 시간대로 변환하는 외부 Provider Port
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import datetime as dt


class TimeZoneProvider(Protocol):
    async def resolve(
        self,
        *,
        latitude: float,
        longitude: float,
        date: dt.date,
    ) -> str: ...
