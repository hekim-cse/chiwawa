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
from chiwawa_backend.services.image_search_client import RemotePhotoPlaceRecognizer
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
    # 데모 모드에서는 토큰 없이 접근하면 고정 데모 유저로 처리한다.
    # (시연에서 로그인 없이 메모리얼 앨범을 보여주기 위한 우회로. 기본값 off.)
    settings = get_settings()
    if credentials is None and settings.memorial_demo_mode:
        return settings.memorial_demo_user_id
    return _user_id_from_credentials(credentials)


def require_user_id_when_enabled(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> int | None:
    """Require a valid user only when production auth is enabled."""
    if not get_settings().require_auth:
        return None
    return _user_id_from_credentials(credentials)


def _user_id_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
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
    settings = get_settings()
    if settings.image_search_url and settings.image_search_url.strip():
        return RemotePhotoPlaceRecognizer(settings)
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
