from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING, Final

from chiwawa_backend.services.local_photo_fs import StoragePathError

if TYPE_CHECKING:
    from pathlib import Path

    from chiwawa_backend.config import Settings

SYSTEM_DIRECTORIES: Final = frozenset({".health", ".trash"})
LEGACY_READINESS_PREFIX: Final = ".ready-"
MAX_SQLITE_INTEGER: Final = (1 << 63) - 1


def validate_photo_root(settings: Settings, root: Path) -> None:
    resolved_root = root.resolve(strict=False)
    if resolved_root.parent == resolved_root:
        raise StoragePathError(root)
    resolved_database = settings.auth_db_path().resolve(strict=False)
    try:
        _ = resolved_database.relative_to(resolved_root)
    except ValueError:
        pass
    else:
        raise StoragePathError(resolved_database)
    try:
        _ = resolved_root.relative_to(resolved_database)
    except ValueError:
        pass
    else:
        raise StoragePathError(root)
    if not root.exists() and not root.is_symlink():
        return
    if root.is_symlink() or not root.is_dir():
        raise StoragePathError(root)
    with os.scandir(root) as entries:
        for entry in entries:
            _validate_entry(root, entry)


def _validate_entry(root: Path, entry: os.DirEntry[str]) -> None:
    path = root / entry.name
    mode = entry.stat(follow_symlinks=False).st_mode
    if entry.name in SYSTEM_DIRECTORIES:
        if not stat.S_ISDIR(mode):
            raise StoragePathError(path)
        return
    if entry.name.startswith(LEGACY_READINESS_PREFIX):
        if not stat.S_ISREG(mode):
            raise StoragePathError(path)
        return
    if not stat.S_ISDIR(mode) or not _is_user_directory(entry.name):
        raise StoragePathError(path)


def _is_user_directory(name: str) -> bool:
    if not name.isascii() or not name.isdecimal():
        return False
    try:
        user_id = int(name)
    except ValueError:
        return False
    return 0 < user_id <= MAX_SQLITE_INTEGER
