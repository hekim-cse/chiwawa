from chiwawa_backend.state import AppState


def get_state() -> AppState:
    message = "state dependency is not configured"
    raise RuntimeError(message)
