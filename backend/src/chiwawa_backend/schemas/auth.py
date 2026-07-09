from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GoogleUserRead(BaseModel):
    id: str
    google_sub: str
    email: str | None = None
    name: str | None = None
    picture: str | None = None
    created_at: datetime
    last_login_at: datetime


class GoogleAuthResponse(BaseModel):
    message: str = Field(default="login successful")
    provider: str = Field(default="google")
    user: GoogleUserRead
