from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    fred_api_key: str = ""
    bls_api_key: str = ""
    eia_api_key: str = ""
    tradier_sandbox_token: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    database_url: str = "sqlite+aiosqlite:///./atlas.db"
    redis_url: str = "redis://localhost:6379"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # Cache TTL seconds
    cache_daily_ohlcv: int = 86400
    cache_intraday: int = 60
    cache_options: int = 900
    cache_ai_plan: int = 86400
    cache_cot: int = 604800
    cache_vix_macro: int = 300

    # Data quality thresholds
    min_gap_ticks: float = 0.25
    max_session_move_pct: float = 0.15
    confidence_low: int = 10
    confidence_med: int = 30
    confidence_high: int = 100

    class Config:
        env_file = ".env"


settings = Settings()
