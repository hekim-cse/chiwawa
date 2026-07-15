from __future__ import annotations

import contextlib
import os
import stat
from pathlib import Path
from typing import Final

DIRECTORY_MODE: Final = 0o700
FILE_MODE: Final = 0o600
READ_CHUNK_BYTES: Final = 1024 * 1024


class StoragePathError(OSError):
    def __init__(self, path: str | Path) -> None:
        self.path: Path = Path(path)
        super().__init__(f"unsafe photo storage path: {self.path}")


def ensure_directory(path: Path) -> None:
    if path.is_symlink():
        raise StoragePathError(path)
    try:
        path.mkdir(mode=DIRECTORY_MODE, parents=True, exist_ok=True)
    except FileExistsError as error:
        raise StoragePathError(path) from error
    path_stat = path.lstat()
    if not stat.S_ISDIR(path_stat.st_mode):
        raise StoragePathError(path)
    path.chmod(DIRECTORY_MODE, follow_symlinks=False)


def durable_write_file(
    root: Path,
    user_part: str,
    file_name: str,
    data: bytes,
) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    ensure_directory(root)
    with contextlib.ExitStack() as stack:
        root_fd = managed_fd(stack, open_directory(root))
        user_fd = managed_fd(
            stack,
            open_or_create_directory_at(
                root_fd,
                user_part,
                root / user_part,
            ),
        )
        os.fsync(root_fd)
        file_fd = managed_fd(
            stack,
            os.open(file_name, flags, FILE_MODE, dir_fd=user_fd),
        )
        try:
            os.fchmod(file_fd, FILE_MODE)
            write_all(file_fd, data)
            os.fsync(file_fd)
            os.fsync(user_fd)
        except (OSError, StoragePathError):
            with contextlib.suppress(OSError):
                os.unlink(file_name, dir_fd=user_fd)
            with contextlib.suppress(OSError):
                os.fsync(user_fd)
            raise


def read_regular_file(
    root: Path,
    user_part: str,
    file_name: str,
    max_bytes: int,
) -> bytes:
    path = root / user_part / file_name
    with contextlib.ExitStack() as stack:
        root_fd = managed_fd(stack, open_directory(root))
        user_fd = managed_fd(
            stack,
            open_directory_at(root_fd, user_part, root / user_part),
        )
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        try:
            file_fd = managed_fd(
                stack,
                os.open(file_name, flags, dir_fd=user_fd),
            )
        except OSError as error:
            raise StoragePathError(path) from error
        file_stat = os.fstat(file_fd)
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size > max_bytes:
            raise StoragePathError(path)
        os.fchmod(file_fd, FILE_MODE)
        data = bytearray()
        while chunk := os.read(file_fd, READ_CHUNK_BYTES):
            data.extend(chunk)
            if len(data) > max_bytes:
                raise StoragePathError(path)
    return bytes(data)


def open_directory(path: Path) -> int:
    try:
        return os.open(path, _directory_flags())
    except OSError as error:
        raise StoragePathError(path) from error


def open_directory_at(parent_fd: int, name: str, path: Path) -> int:
    try:
        return os.open(name, _directory_flags(), dir_fd=parent_fd)
    except OSError as error:
        raise StoragePathError(path) from error


def open_or_create_directory_at(parent_fd: int, name: str, path: Path) -> int:
    with contextlib.suppress(FileExistsError):
        os.mkdir(name, DIRECTORY_MODE, dir_fd=parent_fd)
    directory_fd = open_directory_at(parent_fd, name, path)
    os.fchmod(directory_fd, DIRECTORY_MODE)
    return directory_fd


def managed_fd(stack: contextlib.ExitStack, directory_fd: int) -> int:
    _ = stack.callback(os.close, directory_fd)
    return directory_fd


def require_regular_at(directory_fd: int, name: str, path: Path) -> None:
    file_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if not stat.S_ISREG(file_stat.st_mode):
        raise StoragePathError(path)


def repair_regular_at(directory_fd: int, name: str, path: Path) -> None:
    require_regular_at(directory_fd, name, path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        file_fd = os.open(name, flags, dir_fd=directory_fd)
    except OSError as error:
        raise StoragePathError(path) from error
    try:
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise StoragePathError(path)
        os.fchmod(file_fd, FILE_MODE)
    finally:
        os.close(file_fd)


def regular_file_stat(path: Path) -> os.stat_result:
    if path.is_symlink():
        raise StoragePathError(path)
    file_stat = path.lstat()
    if not stat.S_ISREG(file_stat.st_mode):
        raise StoragePathError(path)
    return file_stat


def write_all(file_fd: int, data: bytes) -> None:
    view = memoryview(data)
    written = 0
    while written < len(view):
        count = os.write(file_fd, view[written:])
        if count <= 0:
            message = "photo write made no progress"
            raise OSError(message)
        written += count


def _directory_flags() -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    return flags | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
