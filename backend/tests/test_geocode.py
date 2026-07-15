from __future__ import annotations

from typing import TYPE_CHECKING, Never

from chiwawa_backend.services import geocode

if TYPE_CHECKING:
    import pytest


def test_reverse_geocode_returns_none_for_non_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")

    class FakeResponse:
        def raise_for_status(self) -> FakeResponse:
            return self

        def json(self) -> Never:
            message = "response is not JSON"
            raise ValueError(message)

    def fake_get(
        _url: str,
        **_kwargs: str | float | dict[str, str],
    ) -> FakeResponse:
        return FakeResponse()

    monkeypatch.setattr("chiwawa_backend.services.geocode.httpx.get", fake_get)

    assert geocode.reverse_geocode(34.69, 135.50) is None
