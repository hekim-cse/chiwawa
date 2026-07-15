from __future__ import annotations

import sqlite3
from threading import Event, Lock, Thread
from typing import TYPE_CHECKING, final

from chiwawa_backend.errors import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType
    from typing import Self


@final
class UploadLeaseHeartbeat:
    def __init__(self, refresh: Callable[[], None], interval_seconds: float) -> None:
        self._refresh = refresh
        self._interval_seconds = interval_seconds
        self._stopped = Event()
        self._failure_lock = Lock()
        self._failure: Exception | None = None
        self._thread = Thread(target=self._run, daemon=True)

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(
        self,
        _exception_type: type[BaseException] | None,
        _exception: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self._stopped.set()
        self._thread.join()

    def ensure_active(self) -> None:
        self._raise_failure()
        self._refresh()
        self._raise_failure()

    def _run(self) -> None:
        while not self._stopped.wait(self._interval_seconds):
            try:
                self._refresh()
            except (ConfigurationError, OSError, sqlite3.Error) as error:
                with self._failure_lock:
                    self._failure = error
                self._stopped.set()

    def _raise_failure(self) -> None:
        with self._failure_lock:
            failure = self._failure
        if failure is not None:
            raise failure
