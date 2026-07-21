# Memorial(회원별 추억) API 테스트
#   cd backend && uv run pytest tests/test_memorial.py

from __future__ import annotations

import contextlib
import datetime as dt
import io
import sqlite3
import time
from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import anyio
import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import ExifTags, Image
from PIL.TiffImagePlugin import IFDRational

from chiwawa_backend.main import create_app
from chiwawa_backend.routers.memorial import MAX_MEMORIAL_PHOTO_SIZE_BYTES
from chiwawa_backend.schemas.auth import GoogleUserProfile
from chiwawa_backend.services import geocode, memorial_photos
from chiwawa_backend.services.auth import save_or_update_user
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.exif import read_exif
from chiwawa_backend.services.jwt_auth import create_access_token
from chiwawa_backend.services.memorial_photos import PhotoUpload

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

# 오사카 도톤보리 근처 좌표
OSAKA_LATITUDE = 34.668736
OSAKA_LONGITUDE = 135.503111


@pytest.fixture
def memorial_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GOOGLE_AUTH_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MEMORIAL_PHOTO_DIR", str(tmp_path / "photos"))
    monkeypatch.setenv("JWT_SECRET", "test-only-secret-at-least-32-characters")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)


@pytest.fixture
def force_kst() -> Iterator[None]:
    # taken_at 정규화가 서버 현지 시간대를 따르므로,
    # +09:00 값을 단언하는 테스트는 어느 머신에서든 KST로 고정한다.
    try:
        with pytest.MonkeyPatch.context() as tz_patch:
            tz_patch.setenv("TZ", "Asia/Seoul")
            time.tzset()
            yield
    finally:
        time.tzset()


def _create_user_token(google_sub: str) -> str:
    user = save_or_update_user(
        GoogleUserProfile(
            sub=google_sub,
            email=f"{google_sub}@test.dev",
            name=google_sub,
        ),
    )
    return create_access_token(subject=user.id)


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


def _jpeg_with_datetime_original(raw: str, offset: str | None = None) -> bytes:
    image = Image.new("RGB", (4, 4), "red")
    exif = Image.Exif()
    exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = raw
    if offset is not None:
        exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.OffsetTimeOriginal] = offset
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


def test_photo_file_is_removed_when_database_connection_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MEMORIAL_PHOTO_DIR", str(tmp_path / "photos"))

    def fail_connect() -> sqlite3.Connection:
        message = "database unavailable"
        raise sqlite3.OperationalError(message)

    monkeypatch.setattr(memorial_photos, "connect", fail_connect)

    with pytest.raises(sqlite3.OperationalError):
        _ = memorial_photos.save_photo(
            7,
            PhotoUpload(
                file_name="photo.png",
                content_type="image/png",
                data=_plain_png(),
                taken_at=None,
                latitude=None,
                longitude=None,
                memo=None,
            ),
        )

    photo_dir = tmp_path / "photos" / "7"
    assert not photo_dir.exists() or not any(photo_dir.iterdir())


@pytest.mark.anyio
@pytest.mark.usefixtures("memorial_env", "force_kst")
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
@pytest.mark.usefixtures("memorial_env", "force_kst")
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


@pytest.mark.anyio
@pytest.mark.usefixtures("memorial_env")
async def test_upload_rejects_invalid_image_bytes() -> None:
    app = create_app()
    token = _create_user_token("memorial-invalid-image")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/memorial/photos",
            headers=_auth_header(token),
            files={"file": ("fake.jpg", b"not an image", "image/jpeg")},
        )

    assert response.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE


@pytest.mark.anyio
@pytest.mark.usefixtures("memorial_env")
async def test_upload_rejects_files_over_size_limit() -> None:
    app = create_app()
    token = _create_user_token("memorial-large-image")
    oversized = b"x" * (MAX_MEMORIAL_PHOTO_SIZE_BYTES + 1)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/memorial/photos",
            headers=_auth_header(token),
            files={"file": ("large.jpg", oversized, "image/jpeg")},
        )

    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE


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


@pytest.mark.anyio
@pytest.mark.usefixtures("memorial_env")
async def test_upload_keeps_event_loop_responsive_during_slow_geocoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: 역지오코딩 API가 1초 동안 응답하지 않는 상황.
    def _slow_reverse_geocode(latitude: float, longitude: float) -> str | None:
        _ = latitude, longitude
        time.sleep(1.0)
        return None

    monkeypatch.setattr(memorial_photos, "reverse_geocode", _slow_reverse_geocode)
    app = create_app()
    token = _create_user_token("memorial-loop-user")
    heartbeats = 0
    upload_done = anyio.Event()
    response: httpx.Response | None = None

    async def _count_heartbeats() -> None:
        nonlocal heartbeats
        while not upload_done.is_set():
            await anyio.sleep(0.05)
            heartbeats += 1

    async with (
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client,
        anyio.create_task_group() as task_group,
    ):
        # When: 업로드가 진행되는 동안 이벤트 루프가 계속 돌 수 있는지 관찰한다.
        _ = task_group.start_soon(_count_heartbeats)
        response = await client.post(
            "/api/v1/memorial/photos",
            headers=_auth_header(token),
            files={"file": ("plain.png", _plain_png(), "image/png")},
            data={
                "latitude": str(OSAKA_LATITUDE),
                "longitude": str(OSAKA_LONGITUDE),
            },
        )
        upload_done.set()

    # Then: 업로드는 성공하고, 그동안 다른 코루틴도 계속 실행됐어야 한다.
    assert response is not None
    assert response.status_code == HTTPStatus.CREATED
    assert heartbeats >= 8


@pytest.mark.anyio
@pytest.mark.usefixtures("memorial_env")
async def test_upload_fallback_taken_at_uses_server_local_timezone() -> None:
    # Given: EXIF도 폼 값도 없는 사진을 KST 서버 환경에서 업로드하는 상황.
    try:
        with pytest.MonkeyPatch.context() as tz_patch:
            tz_patch.setenv("TZ", "Asia/Seoul")
            time.tzset()
            app = create_app()
            token = _create_user_token("memorial-tz-user")

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                # When: 촬영 시각 정보가 전혀 없는 사진을 업로드한다.
                response = await client.post(
                    "/api/v1/memorial/photos",
                    headers=_auth_header(token),
                    files={"file": ("plain.png", _plain_png(), "image/png")},
                )

            # Then: 폴백 taken_at은 UTC가 아니라 서버 현지 시간대여야 한다.
            # (UTC로 저장하면 KST 자정~오전 9시 업로드 사진이 전날로 분류된다.)
            assert response.status_code == HTTPStatus.CREATED
            photo = _json_dict(response)
            taken_at = dt.datetime.fromisoformat(cast("str", photo["taken_at"]))
            assert taken_at.utcoffset() == dt.timedelta(hours=9)
    finally:
        time.tzset()


@pytest.mark.anyio
@pytest.mark.usefixtures("memorial_env")
async def test_upload_normalizes_utc_taken_at_to_local_date_group() -> None:
    # Given: KST 7/20 00:30 촬영을 UTC offset(7/19 15:30Z)으로 표기해 업로드하고,
    #        같은 날 아침 사진은 현지 offset으로 표기해 업로드하는 상황.
    try:
        with pytest.MonkeyPatch.context() as tz_patch:
            tz_patch.setenv("TZ", "Asia/Seoul")
            time.tzset()
            app = create_app()
            token = _create_user_token("memorial-utc-normalize")
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                midnight_response = await client.post(
                    "/api/v1/memorial/photos",
                    headers=_auth_header(token),
                    files={"file": ("midnight.png", _plain_png(), "image/png")},
                    data={"taken_at": "2026-07-19T15:30:00+00:00"},
                )
                morning_response = await client.post(
                    "/api/v1/memorial/photos",
                    headers=_auth_header(token),
                    files={"file": ("morning.png", _plain_png(), "image/png")},
                    data={"taken_at": "2026-07-20T10:00:00+09:00"},
                )
                calendar_response = await client.get(
                    "/api/v1/memorial/calendar",
                    headers=_auth_header(token),
                    params={"year": 2026, "month": 7},
                )
                day_response = await client.get(
                    "/api/v1/memorial/days/2026-07-20",
                    headers=_auth_header(token),
                )
    finally:
        time.tzset()

    # Then: 두 사진 모두 현지 날짜 7/20 하루로 묶이고, 촬영 시각 순서여야 한다.
    assert midnight_response.status_code == HTTPStatus.CREATED
    assert _json_dict(midnight_response)["taken_at"] == "2026-07-20T00:30:00+09:00"
    assert morning_response.status_code == HTTPStatus.CREATED
    calendar = _json_dict(calendar_response)
    assert calendar["days"] == [{"day": "2026-07-20", "photo_count": 2}]
    day = _json_dict(day_response)
    items = cast("list[dict[str, object]]", day["items"])
    photos = [cast("dict[str, object]", item["photo"]) for item in items]
    assert [photo["file_name"] for photo in photos] == ["midnight.png", "morning.png"]


@pytest.mark.usefixtures("memorial_env")
def test_mixed_legacy_taken_at_rows_group_and_sort_by_local_time() -> None:
    # Given: 과거 배포에서 naive/UTC/현지 offset 문자열이 섞여 저장된 상황.
    try:
        with pytest.MonkeyPatch.context() as tz_patch:
            tz_patch.setenv("TZ", "Asia/Seoul")
            time.tzset()
            user = save_or_update_user(
                GoogleUserProfile(
                    sub="memorial-legacy-rows",
                    email="memorial-legacy-rows@test.dev",
                    name="legacy",
                ),
            )
            user_id = int(user.id)
            legacy_rows = [
                ("utc.jpg", "2026-07-19T16:30:00+00:00"),  # KST 2026-07-20 01:30
                ("kst.jpg", "2026-07-20T04:00:00+09:00"),
                ("naive.jpg", "2026-07-20T05:00:00"),
            ]
            with contextlib.closing(connect()) as connection, connection:
                for file_name, taken_at in legacy_rows:
                    _ = connection.execute(
                        """
                        INSERT INTO memorial_photos (
                            user_id, file_name, stored_path, content_type,
                            taken_at, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            file_name,
                            f"/nonexistent/{file_name}",
                            "image/jpeg",
                            taken_at,
                            "2026-07-20T00:00:00+00:00",
                        ),
                    )

            # When: 캘린더와 하루 타임라인을 조회한다.
            calendar = memorial_photos.month_calendar(user_id, 2026, 7)
            day = memorial_photos.day_timeline(user_id, dt.date(2026, 7, 20))
    finally:
        time.tzset()

    # Then: 세 장 모두 현지 날짜 7/20 하루로 묶이고 현지 시각 순서여야 한다.
    assert [(entry.day, entry.photo_count) for entry in calendar.days] == [
        (dt.date(2026, 7, 20), 3),
    ]
    assert [entry.photo.file_name for entry in day.items] == [
        "utc.jpg",
        "kst.jpg",
        "naive.jpg",
    ]


def test_exif_iso_dash_datetime_is_parsed_without_mangling() -> None:
    # Given: 일부 편집기/폰이 쓰는 ISO dash 형식의 EXIF DateTimeOriginal.
    data = read_exif(_jpeg_with_datetime_original("2023-05-01T10:20:30"))

    # Then: 콜론 치환으로 시간 구분자를 망가뜨리지 말고 그대로 파싱해야 한다.
    assert data.taken_at is not None
    assert data.taken_at.isoformat() == "2023-05-01T10:20:30"


def test_exif_iso_dash_datetime_applies_offset_tag() -> None:
    data = read_exif(
        _jpeg_with_datetime_original("2023-05-01T10:20:30", offset="+09:00"),
    )

    assert data.taken_at is not None
    assert data.taken_at.isoformat() == "2023-05-01T10:20:30+09:00"


def test_exif_embedded_offset_is_not_doubled_by_offset_tag() -> None:
    # Given: 촬영 시각 문자열에 이미 offset이 들어 있고 offset 태그도 있는 EXIF.
    data = read_exif(
        _jpeg_with_datetime_original("2023-05-01T10:20:30+02:00", offset="+09:00"),
    )

    # Then: offset을 이어 붙여 파싱을 깨뜨리지 말고 내장 offset을 유지해야 한다.
    assert data.taken_at is not None
    assert data.taken_at.isoformat() == "2023-05-01T10:20:30+02:00"


def test_exif_zero_denominator_gps_yields_no_coordinate() -> None:
    # Given: 위도 DMS의 초(seconds) 분모가 0인 손상된 EXIF 사진.
    # Pillow의 IFDRational(x, 0)은 float() 시 예외 대신 NaN을 반환한다.
    image = Image.new("RGB", (4, 4), "red")
    exif = Image.Exif()
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitudeRef] = "N"
    gps[ExifTags.GPS.GPSLatitude] = (
        IFDRational(34, 1),
        IFDRational(40, 1),
        IFDRational(7, 0),
    )
    gps[ExifTags.GPS.GPSLongitudeRef] = "E"
    gps[ExifTags.GPS.GPSLongitude] = (
        IFDRational(135, 1),
        IFDRational(30, 1),
        IFDRational(11, 1),
    )
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)

    # When: EXIF를 읽는다.
    data = read_exif(buffer.getvalue())

    # Then: NaN이 좌표로 새어나가지 않고 좌표 없음으로 처리돼야 한다.
    assert data.latitude is None
