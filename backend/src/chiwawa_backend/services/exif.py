"""사진 파일의 EXIF에서 촬영 시각과 GPS 좌표를 추출한다."""

from __future__ import annotations

import datetime as dt
import io
import math
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
        ),
        longitude=_coordinate(
            gps,
            value_tag=ExifTags.GPS.GPSLongitude,
            ref_tag=ExifTags.GPS.GPSLongitudeRef,
            negative_ref="W",
        ),
    )


def _taken_at(exif: Image.Exif) -> dt.datetime | None:
    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
    raw: object = exif_ifd.get(ExifTags.Base.DateTimeOriginal) or exif.get(
        ExifTags.Base.DateTime
    )
    if not isinstance(raw, str):
        return None
    # EXIF 형식 "YYYY:MM:DD HH:MM:SS" → ISO 8601 "YYYY-MM-DD HH:MM:SS"
    text = raw.strip().replace(":", "-", 2)
    offset: object = exif_ifd.get(ExifTags.Base.OffsetTimeOriginal)
    if isinstance(offset, str):
        text += offset.strip()
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        return None


def _coordinate(
    gps: dict[int, object],
    *,
    value_tag: int,
    ref_tag: int,
    negative_ref: str,
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
