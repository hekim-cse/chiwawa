from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from chiwawa_backend.services.local_photo_fs import (
    DIRECTORY_MODE,
    managed_fd,
    open_directory,
    open_directory_at,
    repair_regular_at,
    require_regular_at,
)
from chiwawa_backend.services.local_photo_root import (
    LEGACY_READINESS_PREFIX,
    SYSTEM_DIRECTORIES,
)
from chiwawa_backend.services.local_photo_store import StagedDelete

if TYPE_CHECKING:
    from chiwawa_backend.services.local_photo_store import LocalPhotoStore

NO_EXCLUDED_NAMES: Final = frozenset[str]()


@dataclass(frozen=True, slots=True)
class PhotoInventory:
    final_files: tuple[Path, ...]
    staged_deletes: tuple[StagedDelete, ...]


@dataclass(frozen=True, slots=True)
class _OpenedDirectory:
    file_descriptor: int
    path: Path


def scan_photo_inventory(store: LocalPhotoStore) -> PhotoInventory:
    with contextlib.ExitStack() as stack:
        root_fd = managed_fd(stack, open_directory(store.root))
        trash_fd = managed_fd(
            stack,
            open_directory_at(root_fd, ".trash", store.root / ".trash"),
        )
        final_files = _member_files(
            store,
            _OpenedDirectory(root_fd, store.root),
            excluded_names=SYSTEM_DIRECTORIES,
        )
        staged_paths = _member_files(
            store,
            _OpenedDirectory(trash_fd, store.root / ".trash"),
        )
    return PhotoInventory(
        final_files=tuple(final_files),
        staged_deletes=tuple(
            StagedDelete(
                original_path=relative,
                trash_path=store.root / ".trash" / relative,
            )
            for relative in staged_paths
        ),
    )


def _member_files(
    store: LocalPhotoStore,
    parent: _OpenedDirectory,
    *,
    excluded_names: frozenset[str] = NO_EXCLUDED_NAMES,
) -> list[Path]:
    files: list[Path] = []
    with os.scandir(parent.file_descriptor) as member_entries:
        member_names = sorted(
            entry.name for entry in member_entries if entry.name not in excluded_names
        )
    for member_name in member_names:
        if member_name.startswith(LEGACY_READINESS_PREFIX):
            path = parent.path / member_name
            require_regular_at(parent.file_descriptor, member_name, path)
            os.unlink(member_name, dir_fd=parent.file_descriptor)
            os.fsync(parent.file_descriptor)
            continue
        _ = store.parse_stored_path(Path(member_name, "placeholder"))
        member_path = parent.path / member_name
        with contextlib.ExitStack() as stack:
            member_fd = managed_fd(
                stack,
                open_directory_at(
                    parent.file_descriptor,
                    member_name,
                    member_path,
                ),
            )
            os.fchmod(member_fd, DIRECTORY_MODE)
            with os.scandir(member_fd) as file_entries:
                file_names = sorted(entry.name for entry in file_entries)
            for file_name in file_names:
                relative = store.parse_stored_path(Path(member_name, file_name))
                repair_regular_at(member_fd, file_name, member_path / file_name)
                files.append(relative)
    return files
