from functools import lru_cache
from threading import RLock
from typing import Annotated

from ai.image_search.domain.search_schemas import ImageSearchRequest, ImageSearchResult
from ai.image_search.services.place_recognizer import PlaceRecognizer
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import SecretStr

from chiwawa_backend.config import get_settings
from chiwawa_backend.errors import ConfigurationError
from chiwawa_backend.services.jwt_auth import (
    get_current_user_from_credentials,
    security,
)
from chiwawa_backend.services.photo_places import PhotoPlaceRecognizer
from chiwawa_backend.state import AppState


def get_state() -> AppState:
    message = "state dependency is not configured"
    raise RuntimeError(message)


def get_current_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> int:
    claims = get_current_user_from_credentials(credentials)
    subject = claims.sub
    if not subject.isdigit():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token subject",
        )
    return int(subject)


class _LazyPhotoPlaceRecognizer:
    def __init__(self) -> None:
        self._recognizer: PlaceRecognizer | None = None
        self._lock: RLock = RLock()

    def search(self, request: ImageSearchRequest) -> ImageSearchResult:
        recognizer = self._recognizer
        if recognizer is None:
            with self._lock:
                recognizer = self._recognizer
                if recognizer is None:
                    recognizer = _build_photo_place_recognizer()
                    self._recognizer = recognizer
        return recognizer.search(request)


@lru_cache(maxsize=1)
def get_photo_place_recognizer() -> PhotoPlaceRecognizer:
    return _LazyPhotoPlaceRecognizer()


def _build_photo_place_recognizer() -> PlaceRecognizer:
    from ai.image_search.providers.landmark_provider import (  # noqa: PLC0415
        LandmarkProvider,
    )
    from ai.image_search.providers.places_provider import (  # noqa: PLC0415
        PlacesProvider,
    )
    from ai.image_search.providers.vision_llm_provider import (  # noqa: PLC0415
        VisionLlmProvider,
    )

    settings = get_settings()
    try:
        return PlaceRecognizer(
            landmark=LandmarkProvider(
                api_key=_secret_value(settings.google_cloud_vision_api_key),
            ),
            vision_llm=VisionLlmProvider(
                api_key=_secret_value(settings.gemini_api_key),
            ),
            places=PlacesProvider(
                api_key=_secret_value(settings.google_maps_api_key),
            ),
        )
    except ValueError as error:
        raise ConfigurationError(str(error)) from error


def _secret_value(value: SecretStr | None) -> str | None:
    return value.get_secret_value() if value is not None else None
