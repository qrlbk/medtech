"""Application settings loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://medprice:medprice@localhost:5432/medprice"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Meilisearch
    meili_url: str = "http://localhost:7700"
    meili_master_key: str = "masterKey_change_me"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = "change_me_in_prod"
    access_token_expire_minutes: int = 10080
    cors_origins: str = "http://localhost:3000"

    # Normalization
    embeddings_enabled: bool = True
    # "local" = sentence-transformers (offline, free, needs torch);
    # "openai" = OpenAI embeddings API (no torch, needs OPENAI_API_KEY).
    embedding_provider: str = "local"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_openai_model: str = "text-embedding-3-small"
    # Must match the provider's output: local MiniLM = 384, OpenAI 3-small = 1536.
    embedding_dim: int = 384
    normalize_match_threshold: float = 0.78
    normalize_fuzzy_threshold: int = 88

    # Freshness rules (per ТЗ)
    data_fresh_days: int = 30
    raw_retention_days: int = 90

    # LLM arbiter / selector
    llm_enabled: bool = False
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    # How many lexical+semantic candidates to show the LLM selector.
    llm_candidate_k: int = 5

    # Telegram
    telegram_bot_token: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
