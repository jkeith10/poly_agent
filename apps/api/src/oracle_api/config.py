from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORACLE_", env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./oracle.db"
    redis_url: str = "redis://localhost:6379/0"
    polymarket_url: str = "https://gamma-api.polymarket.com"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    default_bankroll: int = 10_000
    auto_create_schema: bool = False
    market_page_size: int = 100
    market_scan_limit: int = 5_000
    admin_api_keys: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_production_credentials(self) -> "Settings":
        if self.environment == "production" and not self.admin_api_keys:
            raise ValueError("ORACLE_ADMIN_API_KEYS is required in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
