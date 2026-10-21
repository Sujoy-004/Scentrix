"""Backend configuration module (minimal)."""

import json
from typing import Annotated, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "sqlite:///./scentrix.db"

    @field_validator("database_url")
    @classmethod
    def pin_postgres_driver(cls, value: str) -> str:
        """Pin the Postgres driver instead of inheriting SQLAlchemy's default.

        SQLAlchemy 2.1 changed the default driver for a bare ``postgresql://``
        URL from psycopg2 to psycopg3. This app ships psycopg2, so on a fresh
        install a bare URL - which is exactly what a managed Postgres provider
        hands out - died at import time with "No module named 'psycopg'".
        The URL is rewritten so the driver is explicit and the app behaves the
        same on every SQLAlchemy version.
        """
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg2://", 1)
        return value

    # NoDecode stops pydantic-settings from json-decoding the env value before
    # the validator runs. Without it a comma-separated ALLOWED_ORIGINS raises
    # SettingsError ("error parsing value for field allowed_origins") because
    # the value is not valid JSON.
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: Any) -> Any:
        """Allow comma-separated strings or a JSON array in ALLOWED_ORIGINS."""
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("["):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    pass
            return [o.strip() for o in raw.split(",") if o.strip()]
        return value


settings = Settings()