from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/xraylogs",
        description="Database connection string for PostgreSQL",
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins for the web dashboard",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
