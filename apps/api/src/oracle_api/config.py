from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORACLE_", env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./oracle.db"
    redis_url: str = "redis://localhost:6379/0"
    polymarket_url: str = "https://gamma-api.polymarket.com"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    default_bankroll: int = 10_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
