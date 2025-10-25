"""
Application settings.

Centralizes environment-driven configuration for the Zeit project so it
can be imported without creating circular dependencies.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    app_name: str = Field("Zeit Project API", env="ZEIT_APP_NAME")
    environment: Literal["dev", "prod", "test"] = Field("dev", env="ZEIT_ENV")
    database_url: str = Field("sqlite:///./test.db", env="ZEIT_DATABASE_URL")
    timezone: str = Field("UTC", env="ZEIT_TIMEZONE")
    data_dir: Path = Field(Path("./data"), env="ZEIT_DATA_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached `Settings` instance."""
    return Settings()
