"""사진 파일의 EXIF에서 촬영 시각과 GPS 좌표를 추출한다."""

from __future__ import annotations

import datetime as dt
import io
import math
import re
from dataclasses import dataclass
from typing import SupportsFloat, cast

from PIL import ExifTags, Image, UnidentifiedImageError
from pillow_heif import (  # pyright: ignore[reportMissingTypeStubs]
    register_heif_opener,  # pyright: ignore[reportUnknownVariableType]
)

register_heif_opener()


@dataclass(frozen=True, slots=True)
class PhotoExif:
    taken_at: dt.datetime | None
    latitude: float | None
    longitude: float | None


EMPTY_EXIF = PhotoExif(taken_at=None, latitude=None, longitude=None)

# GPS 좌표는 (도, 분, 초) 세 부분으로 구성된다.
_DMS_PART_COUNT = 3


# 폼 입력 좌표와 동일한 유효 범위. 손상된 EXIF(예: GPSLatitude 500/1)가
# 검증을 우회하지 못하도록 범위를 벗어난 좌표는 버린다.
_MAX_ABS_LATITUDE = 90.0
_MAX_ABS_LONGITUDE = 180.0

# EXIF 표준 날짜 형식("YYYY:MM:DD ...")인지 판별하는 패턴.
_EXIF_COLON_DATE = re.compile(r"^\d{4}:\d{2}:\d{2}")



class InvalidImageError(ValueError):
    pass


def validate_image(data: bytes) -> None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except (
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as error:
        raise InvalidImageError from error


def read_exif(data: bytes) -> PhotoExif:
    try:
        with Image.open(io.BytesIO(data)) as image:
            exif = image.getexif()
    except (UnidentifiedImageError, OSError, ValueError):
        return EMPTY_EXIF
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    return PhotoExif(
        taken_at=_taken_at(exif),
        latitude=_coordinate(
            gps,
            value_tag=ExifTags.GPS.GPSLatitude,
            ref_tag=ExifTags.GPS.GPSLatitudeRef,
            negative_ref="S",
            max_abs_degrees=_MAX_ABS_LATITUDE,
        ),
        longitude=_coordinate(
            gps,
            value_tag=ExifTags.GPS.GPSLongitude,
            ref_tag=ExifTags.GPS.GPSLongitudeRef,
            negative_ref="W",
            max_abs_degrees=_MAX_ABS_LONGITUDE,
        ),
    )


def _taken_at(exif: Image.Exif) -> dt.datetime | None:
    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
    raw: object = exif_ifd.get(ExifTags.Base.DateTimeOriginal) or exif.get(
        ExifTags.Base.DateTime
    )
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    # EXIF 표준 형식 "YYYY:MM:DD HH:MM:SS"만 ISO 8601로 바꾼다.
    # 일부 편집기는 이미 ISO dash 형식("2023-05-01T10:20:30")을 쓰는데,
    # 그 경우 콜론을 치환하면 시간 구분자가 망가져 파싱에 실패한다.
    if _EXIF_COLON_DATE.match(text):
        text = text.replace(":", "-", 2)
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    offset: object = exif_ifd.get(ExifTags.Base.OffsetTimeOriginal)
    if parsed.tzinfo is None and isinstance(offset, str):
        try:
            return dt.datetime.fromisoformat(text + offset.strip())
        except ValueError:
            return parsed
    return parsed


def _coordinate(
    gps: dict[int, object],
    *,
    value_tag: int,
    ref_tag: int,
    negative_ref: str,
    max_abs_degrees: float,
) -> float | None:
    raw: object = gps.get(value_tag)
    if not isinstance(raw, tuple):
        return None
    values = cast("tuple[object, ...]", raw)
    if len(values) != _DMS_PART_COUNT:
        return None
    parts = [_to_float(part) for part in values]
    if any(part is None for part in parts):
        return None
    degrees, minutes, seconds = (part for part in parts if part is not None)
    decimal = degrees + minutes / 60 + seconds / 3600
    if abs(decimal) > max_abs_degrees:
        return None
    ref: object = gps.get(ref_tag)
    if isinstance(ref, str) and ref.strip().upper() == negative_ref:
        decimal = -decimal
    return decimal


def _to_float(value: object) -> float | None:
    if not isinstance(value, SupportsFloat):
        return None
    try:
        result = float(value)
    except (ValueError, ZeroDivisionError):
        return None
    # Pillow의 IFDRational(x, 0)은 예외 대신 NaN을 반환하므로 여기서 걸러낸다.
    return result if math.isfinite(result) else None
