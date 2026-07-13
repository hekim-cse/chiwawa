# Memorial(회원별 추억) API 테스트
#   cd backend && uv run pytest tests/test_memorial.py

from __future__ import annotations

import io
from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import ExifTags, Image

from chiwawa_backend.main import create_app
from chiwawa_backend.services import geocode
from chiwawa_backend.services.auth import save_or_update_user
from chiwawa_backend.services.jwt_auth import create_access_token

if TYPE_CHECKING:
    from pathlib import Path

# 오사카 도톤보리 근처 좌표
OSAKA_LATITUDE = 34.668736
OSAKA_LONGITUDE = 135.503111


@pytest.fixture
def memorial_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GOOGLE_AUTH_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MEMORIAL_PHOTO_DIR", str(tmp_path / "photos"))
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)


def _create_user_token(google_sub: str) -> str:
    user = save_or_update_user(
        {"sub": google_sub, "email": f"{google_sub}@test.dev", "name": google_sub}
    )
    user_id = cast("object", user["id"])
    return create_access_token(subject=str(user_id))


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _json_dict(response: httpx.Response) -> dict[str, object]:
    return cast("dict[str, object]", response.json())


def _jpeg_with_exif(
    taken_at: str,
    latitude_dms: tuple[float, float, float],
    longitude_dms: tuple[float, float, float],
) -> bytes:
    image = Image.new("RGB", (4, 4), "red")
    exif = Image.Exif()
    exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = taken_at
    exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.OffsetTimeOriginal] = "+09:00"
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitudeRef] = "N"
    gps[ExifTags.GPS.GPSLatitude] = latitude_dms
    gps[ExifTags.GPS.GPSLongitudeRef] = "E"
    gps[ExifTags.GPS.GPSLongitude] = longitude_dms
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


def _plain_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "blue").save(buffer, "PNG")
    return buffer.getvalue()


@pytest.mark.anyio
@pytest.mark.usefixtures("memorial_env")
async def test_upload_extracts_exif_and_builds_day_timeline() -> None:
    app = create_app()
    token = _create_user_token("memorial-user-1")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # 12:05 사진을 먼저 올리고 10:30 사진을 나중에 올려도
        # 타임라인은 촬영 시각 순서여야 한다.
        noon_jpeg = _jpeg_with_exif(
            "2026:07:01 12:05:00",
            latitude_dms=(34.0, 40.0, 7.4),
            longitude_dms=(135.0, 30.0, 11.2),
        )
        noon_response = await client.post(
            "/api/v1/memorial/photos",
            headers=_auth_header(token),
            files={"file": ("noon.jpg", noon_jpeg, "image/jpeg")},
            data={"memo": "도톤보리 점심"},
        )
        assert noon_response.status_code == HTTPStatus.CREATED
        noon_photo = _json_dict(noon_response)
        assert noon_photo["taken_at"] == "2026-07-01T12:05:00+09:00"
        assert noon_photo["latitude"] == pytest.approx(OSAKA_LATITUDE, abs=1e-4)
        assert noon_photo["longitude"] == pytest.approx(OSAKA_LONGITUDE, abs=1e-4)
        assert noon_photo["memo"] == "도톤보리 점심"
        assert noon_photo["address"] is None  # API 키가 없으면 주소는 비워 둔다

        morning_jpeg = _jpeg_with_exif(
            "2026:07:01 10:30:00",
            latitude_dms=(34.0, 39.0, 0.0),
            longitude_dms=(135.0, 29.0, 0.0),
        )
        morning_response = await client.post(
            "/api/v1/memorial/photos",
            headers=_auth_header(token),
            files={"file": ("morning.jpg", morning_jpeg, "image/jpeg")},
        )
        assert morning_response.status_code == HTTPStatus.CREATED

        calendar_response = await client.get(
            "/api/v1/memorial/calendar",
            headers=_auth_header(token),
            params={"year": 2026, "month": 7},
        )
        assert calendar_response.status_code == HTTPStatus.OK
        calendar = _json_dict(calendar_response)
        assert calendar["days"] == [{"day": "2026-07-01", "photo_count": 2}]

        day_response = await client.get(
            "/api/v1/memorial/days/2026-07-01",
            headers=_auth_header(token),
        )
        assert day_response.status_code == HTTPStatus.OK
        day = _json_dict(day_response)
        items = cast("list[dict[str, object]]", day["items"])
        sequences = [item["seq"] for item in items]
        photos = [cast("dict[str, object]", item["photo"]) for item in items]
        file_names = [photo["file_name"] for photo in photos]
        assert sequences == [0, 1]
        assert file_names == ["morning.jpg", "noon.jpg"]

        file_url = noon_photo["file_url"]
        assert isinstance(file_url, str)
        file_response = await client.get(
            file_url,
            headers=_auth_header(token),
        )
        assert file_response.status_code == HTTPStatus.OK
        assert file_response.headers["content-type"] == "image/jpeg"
        assert file_response.content == noon_jpeg


@pytest.mark.anyio
@pytest.mark.usefixtures("memorial_env")
async def test_upload_without_exif_uses_form_fields_and_patch_updates() -> None:
    app = create_app()
    token = _create_user_token("memorial-user-2")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        upload_response = await client.post(
            "/api/v1/memorial/photos",
            headers=_auth_header(token),
            files={"file": ("plain.png", _plain_png(), "image/png")},
            data={
                "taken_at": "2026-07-02T09:00:00+09:00",
                "latitude": str(OSAKA_LATITUDE),
                "longitude": str(OSAKA_LONGITUDE),
            },
        )
        assert upload_response.status_code == HTTPStatus.CREATED
        photo = _json_dict(upload_response)
        assert photo["taken_at"] == "2026-07-02T09:00:00+09:00"
        assert photo["latitude"] == pytest.approx(OSAKA_LATITUDE)

        patch_response = await client.patch(
            f"/api/v1/memorial/photos/{photo['id']}",
            headers=_auth_header(token),
            json={"memo": "오사카성 앞"},
        )
        assert patch_response.status_code == HTTPStatus.OK
        assert _json_dict(patch_response)["memo"] == "오사카성 앞"

        delete_response = await client.delete(
            f"/api/v1/memorial/photos/{photo['id']}",
            headers=_auth_header(token),
        )
        assert delete_response.status_code == HTTPStatus.NO_CONTENT

        missing_response = await client.get(
            f"/api/v1/memorial/photos/{photo['id']}",
            headers=_auth_header(token),
        )
        assert missing_response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.anyio
@pytest.mark.usefixtures("memorial_env")
async def test_memorial_requires_token_and_isolates_users() -> None:
    app = create_app()
    owner_token = _create_user_token("memorial-owner")
    other_token = _create_user_token("memorial-other")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        anonymous_response = await client.get(
            "/api/v1/memorial/calendar",
            params={"year": 2026, "month": 7},
        )
        assert anonymous_response.status_code == HTTPStatus.UNAUTHORIZED

        upload_response = await client.post(
            "/api/v1/memorial/photos",
            headers=_auth_header(owner_token),
            files={"file": ("mine.png", _plain_png(), "image/png")},
        )
        assert upload_response.status_code == HTTPStatus.CREATED
        photo_id = _json_dict(upload_response)["id"]

        stolen_response = await client.get(
            f"/api/v1/memorial/photos/{photo_id}",
            headers=_auth_header(other_token),
        )
        assert stolen_response.status_code == HTTPStatus.NOT_FOUND

        not_image_response = await client.post(
            "/api/v1/memorial/photos",
            headers=_auth_header(owner_token),
            files={"file": ("note.txt", b"not an image", "text/plain")},
        )
        assert not_image_response.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE


def test_reverse_geocode_parses_formatted_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")

    class FakeResponse:
        def raise_for_status(self) -> FakeResponse:
            return self

        def json(self) -> dict[str, object]:
            return {"results": [{"formatted_address": "일본 오사카부 오사카시"}]}

    def fake_get(url: str, **_kwargs: object) -> FakeResponse:
        assert url == geocode.GEOCODE_URL
        return FakeResponse()

    monkeypatch.setattr("chiwawa_backend.services.geocode.httpx.get", fake_get)
    address = geocode.reverse_geocode(OSAKA_LATITUDE, OSAKA_LONGITUDE)
    assert address == "일본 오사카부 오사카시"


def test_reverse_geocode_without_key_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    def fail_get(*_args: object, **_kwargs: object) -> httpx.Response:
        message = "API 키가 없으면 호출 자체가 없어야 한다"
        raise AssertionError(message)

    monkeypatch.setattr("chiwawa_backend.services.geocode.httpx.get", fail_get)
    assert geocode.reverse_geocode(OSAKA_LATITUDE, OSAKA_LONGITUDE) is None
