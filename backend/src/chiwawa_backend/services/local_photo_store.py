from __future__ import annotations

import contextlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from chiwawa_backend.services.local_photo_delete_fs import durable_stage_delete
from chiwawa_backend.services.local_photo_fs import (
    FILE_MODE,
    StoragePathError,
    durable_write_file,
    ensure_directory,
    managed_fd,
    open_directory,
    open_directory_at,
    open_or_create_directory_at,
    read_regular_file,
    regular_file_stat,
    require_regular_at,
)
from chiwawa_backend.services.local_photo_root import validate_photo_root

if TYPE_CHECKING:
    from collections.abc import Callable

    from chiwawa_backend.config import Settings

MAX_SQLITE_INTEGER: Final = (1 << 63) - 1
SAFE_SUFFIXES: Final = frozenset(
    {".avif", ".gif", ".heic", ".jpg", ".png", ".webp"},
)
RELATIVE_PATH_PARTS: Final = 2


@dataclass(frozen=True, slots=True)
class StagedDelete:
    original_path: Path
    trash_path: Path


class LocalPhotoStore:
    def __init__(
        self,
        settings: Settings,
        *,
        name_factory: Callable[[], str] | None = None,
    ) -> None:
        self.root: Path = settings.photo_dir_path()
        self._name_factory: Callable[[], str] = name_factory or (
            lambda: uuid.uuid4().hex
        )
        self._max_photo_bytes: int = settings.max_photo_bytes
        validate_photo_root(settings, self.root)
        ensure_directory(self.root)
        ensure_directory(self.root / ".trash")
        ensure_directory(self.root / ".health")
        with contextlib.ExitStack() as stack:
            root_fd = managed_fd(stack, open_directory(self.root))
            parent_fd = managed_fd(stack, open_directory(self.root.parent))
            os.fsync(root_fd)
            os.fsync(parent_fd)

    def save(self, user_id: int, suffix: str, data: bytes) -> Path:
        if not 0 < user_id <= MAX_SQLITE_INTEGER:
            raise StoragePathError(str(user_id))
        safe_suffix = self._safe_suffix(suffix)
        user_part = str(user_id)
        file_name = f"{self._safe_name(self._name_factory())}{safe_suffix}"
        relative = Path(user_part, file_name)
        durable_write_file(self.root, user_part, file_name, data)
        return relative

    def resolve(self, relative_path: str | Path) -> Path:
        relative = self._relative_path(relative_path)
        ensure_directory(self.root)
        ensure_directory(self.root / relative.parts[0])
        target = self.root / relative
        _ = regular_file_stat(target)
        target.chmod(FILE_MODE, follow_symlinks=False)
        return target

    def read(self, relative_path: str | Path) -> bytes:
        relative = self._relative_path(relative_path)
        user_part, file_name = relative.parts
        return read_regular_file(
            self.root,
            user_part,
            file_name,
            self._max_photo_bytes,
        )

    def normalize_stored_path(self, stored_path: str | Path) -> Path:
        relative = self.parse_stored_path(stored_path)
        _ = self.resolve(relative)
        return relative

    def normalize_user_stored_path(
        self,
        user_id: int,
        stored_path: str | Path,
    ) -> Path:
        relative = self.parse_user_stored_path(user_id, stored_path)
        _ = self.resolve(relative)
        return relative

    def parse_user_stored_path(
        self,
        user_id: int,
        stored_path: str | Path,
    ) -> Path:
        relative = self.parse_stored_path(stored_path)
        if relative.parts[0] != str(user_id):
            raise StoragePathError(stored_path)
        return relative

    def parse_stored_path(self, stored_path: str | Path) -> Path:
        path = Path(stored_path)
        if not path.is_absolute():
            return self._relative_path(path)
        try:
            relative = path.relative_to(self.root)
        except ValueError as error:
            raise StoragePathError(path) from error
        return self._relative_path(relative)

    def stage_delete(self, relative_path: str | Path) -> StagedDelete:
        relative = self.normalize_stored_path(relative_path)
        user_part, file_name = relative.parts
        trash_path = self.root / ".trash" / relative
        durable_stage_delete(self.root, user_part, file_name)
        return StagedDelete(original_path=relative, trash_path=trash_path)

    def restore_delete(self, staged: StagedDelete) -> None:
        relative = self._staged_relative(staged)
        user_part, file_name = relative.parts
        with contextlib.ExitStack() as stack:
            root_fd = managed_fd(stack, open_directory(self.root))
            user_fd = managed_fd(
                stack,
                open_or_create_directory_at(
                    root_fd,
                    user_part,
                    self.root / user_part,
                ),
            )
            os.fsync(root_fd)
            trash_fd = managed_fd(
                stack,
                open_directory_at(root_fd, ".trash", self.root / ".trash"),
            )
            trash_user_fd = managed_fd(
                stack,
                open_directory_at(
                    trash_fd,
                    user_part,
                    self.root / ".trash" / user_part,
                ),
            )
            require_regular_at(trash_user_fd, file_name, staged.trash_path)
            os.link(
                file_name,
                file_name,
                src_dir_fd=trash_user_fd,
                dst_dir_fd=user_fd,
                follow_symlinks=False,
            )
            os.fsync(user_fd)
            os.unlink(file_name, dir_fd=trash_user_fd)
            os.fsync(trash_user_fd)
            with contextlib.suppress(OSError):
                os.rmdir(user_part, dir_fd=trash_fd)
            os.fsync(trash_fd)

    def finalize_delete(self, staged: StagedDelete) -> None:
        relative = self._staged_relative(staged)
        user_part, file_name = relative.parts
        with contextlib.ExitStack() as stack:
            root_fd = managed_fd(stack, open_directory(self.root))
            trash_fd = managed_fd(
                stack,
                open_directory_at(root_fd, ".trash", self.root / ".trash"),
            )
            trash_user_fd = managed_fd(
                stack,
                open_directory_at(
                    trash_fd,
                    user_part,
                    self.root / ".trash" / user_part,
                ),
            )
            require_regular_at(trash_user_fd, file_name, staged.trash_path)
            os.unlink(file_name, dir_fd=trash_user_fd)
            os.fsync(trash_user_fd)
            with contextlib.suppress(OSError):
                os.rmdir(user_part, dir_fd=trash_fd)
            os.fsync(trash_fd)

    def discard(self, relative_path: str | Path) -> None:
        staged = self.stage_delete(relative_path)
        self.finalize_delete(staged)

    @staticmethod
    def _safe_suffix(suffix: str) -> str:
        normalized = suffix.lower()
        if normalized == ".jpeg":
            normalized = ".jpg"
        if normalized not in SAFE_SUFFIXES:
            raise StoragePathError(suffix)
        return normalized

    @staticmethod
    def _safe_name(name: str) -> str:
        if not name or name in {".", ".."} or Path(name).name != name:
            raise StoragePathError(name)
        return name

    @staticmethod
    def _relative_path(path_value: str | Path) -> Path:
        path = Path(path_value)
        if path.is_absolute() or len(path.parts) != RELATIVE_PATH_PARTS:
            raise StoragePathError(path)
        user_part, file_part = path.parts
        if not user_part.isascii() or not user_part.isdecimal():
            raise StoragePathError(path)
        try:
            user_id = int(user_part)
        except ValueError as error:
            raise StoragePathError(path) from error
        if (
            not 0 < user_id <= MAX_SQLITE_INTEGER
            or file_part in {".", ".."}
            or Path(file_part).name != file_part
        ):
            raise StoragePathError(path)
        return Path(user_part, file_part)

    def _staged_relative(self, staged: StagedDelete) -> Path:
        relative = self._relative_path(staged.original_path)
        if staged.trash_path != self.root / ".trash" / relative:
            raise StoragePathError(staged.trash_path)
        return relative
