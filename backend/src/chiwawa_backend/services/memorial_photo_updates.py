import contextlib

from chiwawa_backend.config import Settings
from chiwawa_backend.schemas.memorial import (
    MemorialPhotoItem,
    MemorialPhotoPatchRequest,
)
from chiwawa_backend.services.coordinates import (
    require_coordinate_pair,
    require_coordinate_patch,
)
from chiwawa_backend.services.database import connect
from chiwawa_backend.services.geocode import reverse_geocode
from chiwawa_backend.services.memorial_photo_repository import (
    PhotoUpdate,
    item_from_record,
    require_photo,
    require_photo_on,
)
from chiwawa_backend.services.memorial_photo_repository import (
    update_photo as update_photo_row,
)
from chiwawa_backend.services.patch_values import (
    nullable_patch_value,
    required_patch_value,
)


def update_photo(
    user_id: int,
    photo_id: int,
    patch: MemorialPhotoPatchRequest,
    settings: Settings,
) -> MemorialPhotoItem:
    require_coordinate_patch(
        patch.model_fields_set,
        patch.latitude,
        patch.longitude,
    )
    _ = require_photo(settings, user_id, photo_id)
    proposed_address = (
        _resolve_address(patch.latitude, patch.longitude)
        if "latitude" in patch.model_fields_set
        else None
    )
    with contextlib.closing(connect(settings)) as connection, connection:
        _ = connection.execute("BEGIN IMMEDIATE")
        current = require_photo_on(connection, user_id, photo_id)
        taken_at = required_patch_value(
            patch,
            "taken_at",
            patch.taken_at,
            current.taken_at,
        )
        latitude = nullable_patch_value(
            patch,
            "latitude",
            patch.latitude,
            current.latitude,
        )
        longitude = nullable_patch_value(
            patch,
            "longitude",
            patch.longitude,
            current.longitude,
        )
        require_coordinate_pair(latitude, longitude)
        moved = latitude != current.latitude or longitude != current.longitude
        update_photo_row(
            connection,
            user_id,
            photo_id,
            PhotoUpdate(
                taken_at=taken_at,
                latitude=latitude,
                longitude=longitude,
                address=proposed_address if moved else current.address,
                memo=nullable_patch_value(
                    patch,
                    "memo",
                    patch.memo,
                    current.memo,
                ),
            ),
        )
    return item_from_record(require_photo(settings, user_id, photo_id))


def _resolve_address(latitude: float | None, longitude: float | None) -> str | None:
    if latitude is None or longitude is None:
        return None
    return reverse_geocode(latitude, longitude)
