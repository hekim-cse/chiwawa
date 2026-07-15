"""사진 파일의 EXIF에서 촬영 시각과 GPS 좌표를 추출한다."""

from __future__ import annotations

import datetime as dt
import io
import math
import warnings
from dataclasses import dataclass
from typing import Final, SupportsFloat, cast

from PIL import ExifTags, Image, ImageSequence, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()


@dataclass(frozen=True, slots=True)
class PhotoExif:
    taken_at: dt.datetime | None
    latitude: float | None
    longitude: float | None


EMPTY_EXIF = PhotoExif(taken_at=None, latitude=None, longitude=None)
DETECTED_IMAGE_FORMATS: Final = {
    "AVIF": ("image/avif", ".avif"),
    "GIF": ("image/gif", ".gif"),
    "HEIC": ("image/heic", ".heic"),
    "HEIF": ("image/heif", ".heic"),
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}

# GPS 좌표는 (도, 분, 초) 세 부분으로 구성된다.
_DMS_PART_COUNT = 3


class InvalidImageError(ValueError):
    pass


type ExifScalar = str | bytes | int | float | SupportsFloat | None
type ExifValue = ExifScalar | tuple[ExifScalar, ...]


@dataclass(frozen=True, slots=True)
class ImageInspection:
    content_type: str
    suffix: str
    exif: PhotoExif


def inspect_image(
    data: bytes,
    *,
    max_dimension: int,
    max_pixels: int,
) -> ImageInspection:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                content_type, suffix, exif = _inspect_open_image(
                    image,
                    max_dimension,
                    max_pixels,
                )
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        InvalidImageError,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as error:
        raise InvalidImageError from error
    return ImageInspection(content_type=content_type, suffix=suffix, exif=exif)


def _inspect_open_image(
    image: Image.Image,
    max_dimension: int,
    max_pixels: int,
) -> tuple[str, str, PhotoExif]:
    format_name = image.format
    detected = None if format_name is None else DETECTED_IMAGE_FORMATS.get(format_name)
    if detected is None:
        raise InvalidImageError
    content_type, suffix = detected
    exif = _photo_exif(image.getexif())
    total_pixels = 0
    for frame in ImageSequence.Iterator(image):
        width, height = frame.size
        frame_pixels = width * height
        total_pixels += frame_pixels
        if max(width, height) > max_dimension or total_pixels > max_pixels:
            raise InvalidImageError
        _ = frame.load()
    return content_type, suffix, exif


def validate_image(data: bytes) -> str:
    inspection = inspect_image(
        data,
        max_dimension=2**31 - 1,
        max_pixels=2**63 - 1,
    )
    return inspection.content_type


def read_exif(data: bytes) -> PhotoExif:
    try:
        inspection = inspect_image(
            data,
            max_dimension=2**31 - 1,
            max_pixels=2**63 - 1,
        )
    except InvalidImageError:
        return EMPTY_EXIF
    return inspection.exif


def _photo_exif(exif: Image.Exif) -> PhotoExif:
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
    raw = cast(
        "ExifValue",
        exif_ifd.get(ExifTags.Base.DateTimeOriginal)
        or exif.get(ExifTags.Base.DateTime),
    )
    if not isinstance(raw, str):
        return None
    # EXIF 형식 "YYYY:MM:DD HH:MM:SS" → ISO 8601 "YYYY-MM-DD HH:MM:SS"
    text = raw.strip().replace(":", "-", 2)
    offset = cast("ExifValue", exif_ifd.get(ExifTags.Base.OffsetTimeOriginal))
    if isinstance(offset, str):
        text += offset.strip()
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        return None


def _coordinate(
    gps: dict[int, ExifValue],
    *,
    value_tag: int,
    ref_tag: int,
    negative_ref: str,
) -> float | None:
    raw = gps.get(value_tag)
    if not isinstance(raw, tuple):
        return None
    values = raw
    if len(values) != _DMS_PART_COUNT:
        return None
    parts = [_to_float(part) for part in values]
    if any(part is None for part in parts):
        return None
    degrees, minutes, seconds = (part for part in parts if part is not None)
    decimal = degrees + minutes / 60 + seconds / 3600
    ref = gps.get(ref_tag)
    if isinstance(ref, str) and ref.strip().upper() == negative_ref:
        decimal = -decimal
    return decimal


def _to_float(value: ExifScalar) -> float | None:
    if not isinstance(value, SupportsFloat):
        return None
    try:
        result = float(value)
    except (ValueError, ZeroDivisionError):
        return None
    # Pillow의 IFDRational(x, 0)은 예외 대신 NaN을 반환하므로 여기서 걸러낸다.
    return result if math.isfinite(result) else None
