"""Application settings using Pydantic BaseSettings."""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Database & Cache
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL")
    REDIS_URL: str = Field(..., description="Redis connection URL")

    # APIs
    ALPACA_API_KEY: str | None = None
    ALPACA_SECRET_KEY: str | None = None
    ALPACA_BASE_URL: str | None = None

    BINANCE_API_KEY: str | None = None
    BINANCE_SECRET_KEY: str | None = None
    BINANCE_TESTNET: bool = True

    # Security
    ENCRYPTION_KEY: str = Field(..., min_length=32, description="32-byte key for encryption")
    JWT_SECRET: str = Field(..., min_length=16)

    # Monitoring
    PROMETHEUS_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Trading config
    MAX_PORTFOLIO_RISK: float = 0.02
    MAX_DAILY_DRAWDOWN: float = 0.05
    DEFAULT_POSITION_SIZE: float = 0.01

    # Env
    ENVIRONMENT: str = "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
