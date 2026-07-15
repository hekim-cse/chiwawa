from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Final
from urllib.parse import urlsplit

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from chiwawa_backend.errors import ConfigurationError

MIN_JWT_SECRET_LENGTH: Final = 32
GOOGLE_OAUTH_FIELDS: Final = "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET"
MISSING_GOOGLE_OAUTH_MESSAGE: Final = (
    f"{GOOGLE_OAUTH_FIELDS}, and GOOGLE_REDIRECT_URI are required"
)
MISSING_GOOGLE_CREDENTIAL_MESSAGE: Final = "GOOGLE_CLIENT_SECRET is required"
MISSING_JWT_KEY_MESSAGE: Final = "JWT_SECRET is required"
SHORT_JWT_KEY_MESSAGE: Final = "JWT_SECRET must contain at least 32 characters"
INSECURE_COOKIE_MESSAGE: Final = "GOOGLE_OAUTH_COOKIE_SECURE must be enabled"
MISSING_DATABASE_PATH_MESSAGE: Final = "DATABASE_PATH is required"
RELATIVE_DATABASE_PATH_MESSAGE: Final = "DATABASE_PATH must be absolute"
RELATIVE_PHOTO_DIR_MESSAGE: Final = "MEMORIAL_PHOTO_DIR must be absolute"
INSECURE_GOOGLE_REDIRECT_MESSAGE: Final = "GOOGLE_REDIRECT_URI must use HTTPS"


class DeploymentMode(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


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

    app_env: DeploymentMode = DeploymentMode.DEVELOPMENT
    database_path: Path | None = None
    memorial_photo_dir: Path = Path("data/memorial_photos")
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str | None = None
    google_auth_db_path: Path = Path("data/google_auth.db")
    google_oauth_cookie_secure: bool = False
    google_oauth_state_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    jwt_secret: SecretStr | None = None
    max_json_body_bytes: int = Field(default=1024 * 1024, ge=1)
    max_multipart_body_bytes: int = Field(default=12 * 1024 * 1024, ge=1)
    max_photo_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    max_photos_per_user: int = Field(default=1000, ge=1)
    max_photo_bytes_per_user: int = Field(default=2 * 1024 * 1024 * 1024, ge=1)
    max_uploads_per_user_per_hour: int = Field(default=60, ge=1)
    max_concurrent_uploads: int = Field(default=8, ge=1)
    max_concurrent_uploads_per_user: int = Field(default=2, ge=1)
    upload_lease_ttl_seconds: int = Field(default=300, ge=1)
    max_image_pixels: int = Field(default=40_000_000, ge=1)
    max_image_dimension: int = Field(default=16_384, ge=1)
    min_free_disk_bytes: int = Field(default=1024 * 1024 * 1024, ge=1)
    sqlite_busy_timeout_ms: int = Field(default=5000, ge=1)

    @property
    def is_production(self) -> bool:
        return self.app_env is DeploymentMode.PRODUCTION

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

    def auth_db_path(self) -> Path:
        configured_path = self.database_path
        path = (
            self.google_auth_db_path if configured_path is None else configured_path
        ).expanduser()
        return path if path.is_absolute() else (Path.cwd() / path).resolve()

    def photo_dir_path(self) -> Path:
        path = self.memorial_photo_dir.expanduser()
        return path if path.is_absolute() else (Path.cwd() / path).resolve()

    def validate_production(self) -> None:
        if not self.is_production:
            return
        _ = self.require_jwt_secret()
        google_oauth = self.require_google_oauth()
        redirect = urlsplit(google_oauth.redirect_uri)
        if redirect.scheme.lower() != "https" or not redirect.hostname:
            raise ConfigurationError(INSECURE_GOOGLE_REDIRECT_MESSAGE)
        if not self.google_oauth_cookie_secure:
            raise ConfigurationError(INSECURE_COOKIE_MESSAGE)
        if self.database_path is None:
            raise ConfigurationError(MISSING_DATABASE_PATH_MESSAGE)
        if not self.database_path.is_absolute():
            raise ConfigurationError(RELATIVE_DATABASE_PATH_MESSAGE)
        if not self.memorial_photo_dir.is_absolute():
            raise ConfigurationError(RELATIVE_PHOTO_DIR_MESSAGE)


def get_settings() -> Settings:
    return Settings()
