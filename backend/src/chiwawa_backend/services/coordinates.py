import math

from chiwawa_backend.errors import DomainValidationError

COORDINATE_PAIR_ERROR = "latitude and longitude must be provided together"
COORDINATE_RANGE_ERROR = "latitude or longitude is outside the valid range"
COORDINATE_FIELDS = frozenset({"latitude", "longitude"})
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0


def require_coordinate_pair(
    latitude: float | None,
    longitude: float | None,
) -> None:
    if (latitude is None) != (longitude is None):
        raise DomainValidationError(COORDINATE_PAIR_ERROR)
    if latitude is None or longitude is None:
        return
    if (
        not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not MIN_LATITUDE <= latitude <= MAX_LATITUDE
        or not MIN_LONGITUDE <= longitude <= MAX_LONGITUDE
    ):
        raise DomainValidationError(COORDINATE_RANGE_ERROR)


def require_coordinate_patch(
    fields_set: set[str],
    latitude: float | None,
    longitude: float | None,
) -> None:
    supplied = fields_set & COORDINATE_FIELDS
    if supplied and len(supplied) != len(COORDINATE_FIELDS):
        raise DomainValidationError(COORDINATE_PAIR_ERROR)
    if supplied:
        require_coordinate_pair(latitude, longitude)


def complete_coordinate_pair(
    latitude: float | None,
    longitude: float | None,
) -> tuple[float | None, float | None]:
    try:
        require_coordinate_pair(latitude, longitude)
    except DomainValidationError:
        return None, None
    return latitude, longitude
