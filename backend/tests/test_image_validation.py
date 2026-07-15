from __future__ import annotations

import io
from typing import TYPE_CHECKING

import pytest
from PIL import Image

from chiwawa_backend.services.exif import InvalidImageError, inspect_image

if TYPE_CHECKING:
    from collections.abc import Sequence


def _animated_gif(colors: Sequence[str]) -> bytes:
    frames = [Image.new("RGB", (4, 4), color) for color in colors]
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        "GIF",
        save_all=True,
        append_images=frames[1:],
    )
    return buffer.getvalue()


def test_inspection_rejects_truncated_later_gif_frame() -> None:
    # Given: frame zero decodes but the second GIF frame is truncated.
    truncated = _animated_gif(("red", "blue"))[:-3]
    with Image.open(io.BytesIO(truncated)) as image:
        _ = image.load()
        image.seek(1)
        with pytest.raises(OSError, match="truncated"):
            _ = image.load()

    # When/Then: whole-image inspection rejects the hidden decoder failure.
    with pytest.raises(InvalidImageError):
        _ = inspect_image(truncated, max_dimension=10, max_pixels=100)


def test_inspection_applies_pixel_budget_across_all_frames() -> None:
    # Given: two valid 16-pixel frames exceed a 20-pixel aggregate budget.
    animated = _animated_gif(("red", "blue"))

    # When/Then: cumulative decoded pixels are rejected even if each frame fits.
    with pytest.raises(InvalidImageError):
        _ = inspect_image(animated, max_dimension=10, max_pixels=20)
