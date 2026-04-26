"""Application settings loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized config. Reads from .env and environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM ---
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    llm_model: str = "claude-sonnet-4-5-20250929"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # --- Embeddings ---
    embedding_model: Literal["local", "openai"] = "local"
    local_embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"

    # --- Verification ---
    github_token: str | None = None

    # --- Auth (Clerk) ---
    clerk_jwks_url: str | None = None
    clerk_audience: str | None = None
    clerk_issuer: str | None = None
    dev_bypass_auth: bool = False

    # --- Cache ---
    redis_url: str | None = None

    # --- CORS ---
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
