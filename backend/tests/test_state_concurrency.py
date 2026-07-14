from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from threading import Event

from chiwawa_backend.schemas.schedule import ScheduleItemCreateRequest
from chiwawa_backend.schemas.trips import TripCreateRequest
from chiwawa_backend.services.schedule import create_schedule_item, list_schedule
from chiwawa_backend.services.trips import create_trip
from chiwawa_backend.state import AppState


def test_schedule_reads_and_writes_share_state_lock() -> None:
    # Given: concurrent readers and writers using the same development state store.
    original_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        state = AppState()
        trip = create_trip(
            state,
            TripCreateRequest(
                city="Tokyo",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
            ),
        )
        payload = ScheduleItemCreateRequest(
            name="Concurrent stop",
            date=date(2026, 1, 1),
            start_time=time(1),
            end_time=time(2),
        )
        for _ in range(10_000):
            _ = create_schedule_item(state, trip.id, payload)

        stop = Event()
        errors: list[str] = []

        def reader() -> None:
            for _ in range(500):
                try:
                    _ = list_schedule(state, trip.id)
                except RuntimeError as exc:
                    errors.append(str(exc))
                    stop.set()
                    return
            stop.set()

        def writer() -> None:
            while not stop.is_set():
                _ = create_schedule_item(state, trip.id, payload)

        # When: a list iteration races with schedule insertion.
        with ThreadPoolExecutor(max_workers=2) as executor:
            reader_future = executor.submit(reader)
            writer_future = executor.submit(writer)
            _ = reader_future.result()
            _ = writer_future.result()

        # Then: shared locking prevents dictionary-size iteration failures.
        assert errors == []
    finally:
        sys.setswitchinterval(original_interval)
