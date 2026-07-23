from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from chiwawa_backend.errors import ConfigurationError

MIN_JWT_SECRET_LENGTH = 32
GOOGLE_OAUTH_FIELDS = "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET"
MISSING_GOOGLE_OAUTH_MESSAGE = (
    f"{GOOGLE_OAUTH_FIELDS}, and GOOGLE_REDIRECT_URI are required"
)
MISSING_GOOGLE_CREDENTIAL_MESSAGE = "GOOGLE_CLIENT_SECRET is required"
MISSING_JWT_KEY_MESSAGE = "JWT_SECRET is required"
SHORT_JWT_KEY_MESSAGE = "JWT_SECRET must contain at least 32 characters"
MISSING_IMAGE_SEARCH_URL_MESSAGE = "IMAGE_SEARCH_URL is required"


@dataclass(frozen=True, slots=True)
class GoogleOAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str | None = None
    google_auth_db_path: Path = Path("data/google_auth.db")
    google_oauth_cookie_secure: bool = False
    google_oauth_state_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    jwt_secret: SecretStr | None = None
    google_maps_api_key: SecretStr | None = None
    google_cloud_vision_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    image_search_url: str | None = None
    image_search_timeout_seconds: float = Field(default=125.0, ge=1, le=180)
    image_search_max_retries: int = Field(default=1, ge=0, le=2)
    cors_allow_origins: str = "http://localhost:8080"
    # 데모 모드: 토큰 없이(게스트) 접근 시 고정 데모 유저로 처리한다.
    # 시연에서 로그인 없이 메모리얼 앨범을 보여주기 위한 용도. 기본값 off.
    memorial_demo_mode: bool = False
    memorial_demo_user_id: int = 1

    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]

    def require_google_oauth(self) -> GoogleOAuthConfig:
        client_id = self.google_client_id
        client_secret = self.google_client_secret
        redirect_uri = self.google_redirect_uri
        if not client_id or client_secret is None or not redirect_uri:
            raise ConfigurationError(MISSING_GOOGLE_OAUTH_MESSAGE)
        secret = client_secret.get_secret_value()
        if not secret:
            raise ConfigurationError(MISSING_GOOGLE_CREDENTIAL_MESSAGE)
        return GoogleOAuthConfig(
            client_id=client_id,
            client_secret=secret,
            redirect_uri=redirect_uri,
        )

    def require_jwt_secret(self) -> str:
        if self.jwt_secret is None:
            raise ConfigurationError(MISSING_JWT_KEY_MESSAGE)
        secret = self.jwt_secret.get_secret_value()
        if len(secret) < MIN_JWT_SECRET_LENGTH:
            raise ConfigurationError(SHORT_JWT_KEY_MESSAGE)
        return secret

    def require_image_search_url(self) -> str:
        if self.image_search_url is None or not self.image_search_url.strip():
            raise ConfigurationError(MISSING_IMAGE_SEARCH_URL_MESSAGE)
        return self.image_search_url.strip()

    def auth_db_path(self) -> Path:
        path = self.google_auth_db_path.expanduser()
        return path if path.is_absolute() else (Path.cwd() / path).resolve()


def get_settings() -> Settings:
    return Settings()
