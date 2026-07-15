from dataclasses import fields

from chiwawa_backend.state import AppState


def test_app_state_excludes_oauth_runtime_storage() -> None:
    # Given: AppState is the durable travel aggregate.
    field_names = {item.name for item in fields(AppState)}

    # When/Then: OAuth's separately persisted runtime state is not part of it.
    assert "oauth_states" not in field_names
