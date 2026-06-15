"""Environment-backed application settings with startup validation."""

from __future__ import annotations

import re
from datetime import timedelta
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_jwt_expiry(value: str) -> timedelta:
    """Parse JWT expiry strings compatible with the Node backend (e.g. 365d)."""
    trimmed = value.strip()
    day_match = re.fullmatch(r"(\d+)d", trimmed)
    if day_match:
        return timedelta(days=int(day_match.group(1)))
    hour_match = re.fullmatch(r"(\d+)h", trimmed)
    if hour_match:
        return timedelta(hours=int(hour_match.group(1)))
    return timedelta(days=365)


class Settings(BaseSettings):
    """Validated configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    port: int = Field(default=3000, alias="PORT")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    mongodb_uri: str = Field(
        default="mongodb://127.0.0.1:27017/english-guru",
        alias="MONGODB_URI",
    )
    mongodb_db_name: str | None = Field(default=None, alias="MONGODB_DB_NAME")
    firebase_project_id: str = Field(alias="FIREBASE_PROJECT_ID")
    firebase_client_email: str = Field(alias="FIREBASE_CLIENT_EMAIL")
    firebase_private_key: str = Field(alias="FIREBASE_PRIVATE_KEY")
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_access_token_expiry: str = Field(default="365d", alias="JWT_ACCESS_TOKEN_EXPIRY")
    allowed_hosts: str | None = Field(default=None, alias="ALLOWED_HOSTS")

    @field_validator("firebase_private_key")
    @classmethod
    def normalize_private_key(cls, value: str) -> str:
        return value.replace("\\n", "\n").strip()

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def jwt_expiry_delta(self) -> timedelta:
        return _parse_jwt_expiry(self.jwt_access_token_expiry)

    @property
    def trusted_hosts(self) -> list[str] | None:
        if not self.allowed_hosts:
            return None
        hosts = [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]
        return hosts or None


@lru_cache
def get_settings() -> Settings:
    """Return cached settings; raises validation errors on startup if env is invalid."""
    return Settings()  # type: ignore[call-arg]
