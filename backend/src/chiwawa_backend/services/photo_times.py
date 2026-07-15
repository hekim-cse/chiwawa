import datetime as dt
from zoneinfo import ZoneInfo

from chiwawa_backend.errors import ConfigurationError

TOKYO_TIMEZONE = ZoneInfo("Asia/Tokyo")
MONTHS_PER_YEAR = 12


def normalize_photo_time(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=TOKYO_TIMEZONE)
    return value.astimezone(TOKYO_TIMEZONE)


def photo_time_columns(value: dt.datetime) -> tuple[dt.datetime, str, str]:
    local = normalize_photo_time(value)
    return (
        local,
        local.astimezone(dt.UTC).isoformat(),
        local.date().isoformat(),
    )


def current_photo_time() -> dt.datetime:
    return dt.datetime.now(TOKYO_TIMEZONE).replace(microsecond=0)


def photo_month_bounds(month_prefix: str) -> tuple[str, str]:
    month_start = dt.date.fromisoformat(f"{month_prefix}-01")
    if month_start.month == MONTHS_PER_YEAR:
        month_end = dt.date(month_start.year + 1, 1, 1)
    else:
        month_end = dt.date(month_start.year, month_start.month + 1, 1)
    return month_start.isoformat(), month_end.isoformat()


def utc_sort_instant(value: str) -> dt.datetime:
    try:
        instant = dt.datetime.fromisoformat(value)
    except ValueError as error:
        message = "taken_at_utc must be an ISO 8601 timestamp"
        raise ConfigurationError(message) from error
    if instant.tzinfo is None or instant.utcoffset() is None:
        message = "taken_at_utc must be timezone-aware"
        raise ConfigurationError(message)
    return instant.astimezone(dt.UTC)
