"""
Centralized configuration via environment variables.

Uses pydantic-settings to upload, validate and type all settings
the design from environment variables.

Usage:
    from media_generator_graph.shared.configurations_factory import settings

All settings have sensible default values for local development.
In production, configure via .env.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- ENVIRONMENT ---
    environment: str = "development"

    # --- LLM (OpenRouter) ---
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_text_model: str = "google/gemini-2.5-flash-lite"
    openrouter_media_model: str = "google/gemini-2.5-flash-lite"
    ## --- Memory (LangGraph Store) ---
    openrouter_embedding_model: str = "openai/text-embedding-3-small"
    embedding_dims: int = 1536
    memory_search_limit: int = 5

    # --- DATABASE ---
    database_url: str = ""
    database_pool_min_size: int = 1
    database_pool_max_size: int = 10
    database_pool_open_timeout: float = 10.0

    # --- LLM RATE LIMIT ---
    llm_rate_limit_requests_per_second: float = 0.5
    llm_rate_limit_max_burst: int = 10


settings = AppSettings()
