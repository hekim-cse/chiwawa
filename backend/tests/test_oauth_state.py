from datetime import UTC, datetime, timedelta

from chiwawa_backend.state import AppState


def test_oauth_state_is_invalid_at_exact_expiration() -> None:
    state = AppState()
    expires_at = datetime.now(UTC) + timedelta(minutes=1)
    state.issue_oauth_state("x" * 43, expires_at)

    assert state.consume_oauth_state("x" * 43, expires_at) is False
