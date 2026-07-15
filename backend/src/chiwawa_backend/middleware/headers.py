from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.datastructures import Headers

if TYPE_CHECKING:
    from starlette.types import Scope


def normalized_headers(scope: Scope) -> Headers:
    raw_headers = Headers(scope=scope).raw
    return Headers(raw=[(name.lower(), value) for name, value in raw_headers])
