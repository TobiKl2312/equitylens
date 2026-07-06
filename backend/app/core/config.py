from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://equitylens:equitylens@localhost:5432/equitylens"

    # SEC EDGAR rejects requests without a descriptive User-Agent incl. contact
    edgar_user_agent: str = "EquityLens/0.1 (contact@example.com)"

    # Week 2+ (RAG)
    anthropic_api_key: str = ""
    voyage_api_key: str = ""

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
