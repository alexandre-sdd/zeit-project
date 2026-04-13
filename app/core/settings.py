"""
Application settings.

Centralizes environment-driven configuration for the Zeit project so it
can be imported without creating circular dependencies.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field("Zeit Project API", validation_alias="ZEIT_APP_NAME")
    environment: Literal["dev", "prod", "test"] = Field("dev", validation_alias="ZEIT_ENV")
    database_url: str = Field("sqlite:///./test.db", validation_alias="ZEIT_DATABASE_URL")
    timezone: str = Field("UTC", validation_alias="ZEIT_TIMEZONE")
    data_dir: Path = Field(Path("./data"), validation_alias="ZEIT_DATA_DIR")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached `Settings` instance."""
    return Settings()
