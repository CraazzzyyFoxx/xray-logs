from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str = (
        "postgresql+asyncpg://xray_logs:xray_logs@localhost:5432/xray_logs"
    )
    cors_allow_origins: List[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_prefix="XRAY_", env_nested_delimiter="__")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
