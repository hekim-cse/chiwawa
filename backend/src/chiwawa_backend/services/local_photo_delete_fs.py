import contextlib
import os
from pathlib import Path

from chiwawa_backend.services.local_photo_fs import (
    managed_fd,
    open_directory,
    open_directory_at,
    open_or_create_directory_at,
    require_regular_at,
)


def durable_stage_delete(root: Path, user_part: str, file_name: str) -> None:
    relative = Path(user_part, file_name)
    with contextlib.ExitStack() as stack:
        root_fd = managed_fd(stack, open_directory(root))
        user_fd = managed_fd(
            stack,
            open_directory_at(root_fd, user_part, root / user_part),
        )
        trash_fd = managed_fd(
            stack,
            open_directory_at(root_fd, ".trash", root / ".trash"),
        )
        trash_user_fd = managed_fd(
            stack,
            open_or_create_directory_at(
                trash_fd,
                user_part,
                root / ".trash" / user_part,
            ),
        )
        os.fsync(trash_fd)
        require_regular_at(user_fd, file_name, root / relative)
        linked = False
        source_unlinked = False
        try:
            os.link(
                file_name,
                file_name,
                src_dir_fd=user_fd,
                dst_dir_fd=trash_user_fd,
                follow_symlinks=False,
            )
            linked = True
            os.fsync(trash_user_fd)
            os.unlink(file_name, dir_fd=user_fd)
            source_unlinked = True
            os.fsync(user_fd)
        except OSError:
            restored = not source_unlinked
            if source_unlinked:
                try:
                    os.link(
                        file_name,
                        file_name,
                        src_dir_fd=trash_user_fd,
                        dst_dir_fd=user_fd,
                        follow_symlinks=False,
                    )
                    os.fsync(user_fd)
                    restored = True
                except OSError:
                    restored = False
            if linked and restored:
                with contextlib.suppress(OSError):
                    os.unlink(file_name, dir_fd=trash_user_fd)
            with contextlib.suppress(OSError):
                os.fsync(trash_user_fd)
            raise
