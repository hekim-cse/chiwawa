# 여행·장소·확정 일정 SQLite 영속화 경계를 검증하는 통합 테스트
from datetime import date, time
from pathlib import Path

import pytest

from chiwawa_backend.errors import ConfigurationError
from chiwawa_backend.schemas.places import WantedPlaceCreateRequest
from chiwawa_backend.schemas.plans import ConfirmedRouteOptimizationRead
from chiwawa_backend.schemas.schedule import ScheduleItemCreateRequest
from chiwawa_backend.schemas.trips import TripCreateRequest
from chiwawa_backend.services.schedule import create_schedule_item, list_schedule
from chiwawa_backend.services.state_store import SQLiteStateStore
from chiwawa_backend.services.trips import create_trip, delete_trip, list_trips
from chiwawa_backend.services.wanted_places import (
    create_wanted_place,
    list_wanted_places,
)
from chiwawa_backend.state import AppState


def _state(database_path: Path) -> AppState:
    return AppState(store=SQLiteStateStore(database_path))


def test_trip_place_and_confirmed_schedule_survive_state_recreation(
    tmp_path: Path,
) -> None:
    # Given: 실제 서비스와 같은 SQLite 저장소를 사용하는 상태에서 여행을 생성한다.
    database_path = tmp_path / "chiwawa.db"
    state = _state(database_path)
    trip = create_trip(
        state,
        TripCreateRequest(
            country="France",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 2),
        ),
    )
    place = create_wanted_place(
        state,
        trip.id,
        WantedPlaceCreateRequest(
            provider_place_id="eiffel-place-id",
            name="에펠탑",
            city="Paris",
            country="France",
            latitude=48.8584,
            longitude=2.2945,
        ),
    )
    schedule = create_schedule_item(
        state,
        trip.id,
        ScheduleItemCreateRequest(
            name=place.name,
            date=trip.start_date,
            start_time=time(10),
            end_time=time(11, 30),
            place_id=place.id,
        ),
    )
    state.confirmed_route_items[(trip.id, 1)] = [schedule.id]
    state.confirmed_routes[(trip.id, 1)] = (
        ConfirmedRouteOptimizationRead.model_validate(
            {
                "day_index": 1,
                "start": {
                    "place_id": "hotel",
                    "name": "파리 숙소",
                    "lat": 48.8566,
                    "lng": 2.3522,
                },
                "end": {
                    "place_id": "hotel",
                    "name": "파리 숙소",
                    "lat": 48.8566,
                    "lng": 2.3522,
                },
                "route": {
                    "trip_id": trip.id,
                    "transport_mode": "walk",
                    "stops": [
                        {
                            "order": 1,
                            "place_id": place.id,
                            "name": place.name,
                            "estimated_travel_minutes": 20,
                        },
                    ],
                    "total_estimated_minutes": 40,
                    "timeline": {
                        "day_index": 1,
                        "travel_mode": "WALK",
                        "planned_start_at": "2026-08-01T09:00:00+02:00",
                        "planned_end_at": "2026-08-01T20:00:00+02:00",
                        "actual_end_at": "2026-08-01T11:10:00+02:00",
                        "total_travel_minutes": 40,
                        "total_stay_minutes": 90,
                        "timeline_stops": [
                            {
                                "stop_type": "START",
                                "place_id": "hotel",
                                "name": "파리 숙소",
                                "arrival_at": "2026-08-01T09:00:00+02:00",
                                "departure_at": "2026-08-01T09:00:00+02:00",
                                "stay_minutes": 0,
                            },
                            {
                                "stop_type": "POI",
                                "place_id": place.id,
                                "name": place.name,
                                "arrival_at": "2026-08-01T09:20:00+02:00",
                                "departure_at": "2026-08-01T10:50:00+02:00",
                                "stay_minutes": 90,
                            },
                            {
                                "stop_type": "END",
                                "place_id": "hotel",
                                "name": "파리 숙소",
                                "arrival_at": "2026-08-01T11:10:00+02:00",
                                "departure_at": "2026-08-01T11:10:00+02:00",
                                "stay_minutes": 0,
                            },
                        ],
                    },
                },
            },
        )
    )
    # 직접 변경된 경로 확정 메타데이터도 같은 트랜잭션에 반영한다.
    state.persist()

    # When: Backend 재시작과 동일하게 AppState와 SQLite 연결을 다시 만든다.
    restored = _state(database_path)

    # Then: API 서비스가 기존 계약 그대로 영속 데이터를 조회한다.
    assert trip.city is None
    assert list_trips(restored).items == [trip]
    assert list_wanted_places(restored, trip.id).items == [place]
    assert list_schedule(restored, trip.id).items == [schedule]
    assert restored.confirmed_route_items[(trip.id, 1)] == [schedule.id]
    assert restored.confirmed_routes[(trip.id, 1)].start.name == "파리 숙소"
    assert (
        len(
            restored.confirmed_routes[(trip.id, 1)].route.timeline.timeline_stops,
        )
        == 3
    )


def test_deleting_trip_removes_persisted_children(tmp_path: Path) -> None:
    # Given: 장소와 일정이 포함된 여행이 SQLite에 저장되어 있다.
    database_path = tmp_path / "chiwawa.db"
    state = _state(database_path)
    trip = create_trip(
        state,
        TripCreateRequest(
            city="Paris",
            country="France",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 1),
        ),
    )
    _ = create_wanted_place(
        state,
        trip.id,
        WantedPlaceCreateRequest(name="루브르 박물관"),
    )
    _ = create_schedule_item(
        state,
        trip.id,
        ScheduleItemCreateRequest(
            name="루브르 박물관",
            date=trip.start_date,
            start_time=time(14),
            end_time=time(16),
        ),
    )

    # When: 여행을 삭제하고 Backend 상태를 새로 생성한다.
    delete_trip(state, trip.id)
    restored = _state(database_path)

    # Then: 부모와 종속 데이터가 함께 제거되어 고아 데이터가 남지 않는다.
    assert list_trips(restored).items == []
    assert restored.wanted_places == {}
    assert restored.schedule_items == {}


def test_invalid_application_database_target_is_rejected(tmp_path: Path) -> None:
    # Given: SQLite 파일 대신 디렉터리가 설정되어 있다.
    invalid_path = tmp_path / "database-directory"
    invalid_path.mkdir()

    # When / Then: 숨겨진 대체 경로 없이 설정 오류를 명시적으로 반환한다.
    with pytest.raises(ConfigurationError, match="APP_DB_PATH"):
        _ = SQLiteStateStore(invalid_path)
