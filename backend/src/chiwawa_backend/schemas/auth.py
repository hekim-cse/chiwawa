from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import ClassVar

from pydantic import ConfigDict, Field

from chiwawa_backend.schemas.base import ApiModel


class GoogleProviderModel(ApiModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")


class GoogleTokenResponse(GoogleProviderModel):
    access_token: str = Field(min_length=1)
    token_type: str | None = None
    expires_in: int | None = Field(default=None, ge=1)
    scope: str | None = None
    id_token: str | None = None
    refresh_token: str | None = None
    refresh_token_expires_in: int | None = Field(default=None, ge=1)


class GoogleUserProfile(GoogleProviderModel):
    sub: str = Field(min_length=1)
    email: str | None = None
    email_verified: bool | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None
    locale: str | None = None
    hd: str | None = None


class GoogleUserRead(ApiModel):
    id: str
    google_sub: str
    email: str | None = None
    name: str | None = None
    picture: str | None = None
    created_at: dt.datetime
    last_login_at: dt.datetime


class TokenIdentity(ApiModel):
    email: str | None = None
    name: str | None = None


class AccessTokenClaims(TokenIdentity):
    sub: str = Field(min_length=1)
    iat: dt.datetime
    exp: dt.datetime


class CurrentUserRead(TokenIdentity):
    sub: str = Field(min_length=1)


class TokenType(StrEnum):
    BEARER = "bearer"


class GoogleAuthResponse(ApiModel):
    message: str = "login successful"
    provider: str = "google"
    token_type: TokenType = TokenType.BEARER
    access_token: str = Field(min_length=1)
    user: GoogleUserRead
