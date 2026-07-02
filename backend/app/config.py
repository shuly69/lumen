"""Application settings, loaded from the environment (12-factor style)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LUMEN_", env_file=".env", extra="ignore")

    # Anthropic
    anthropic_api_key: str = ""
    model: str = "claude-opus-4-8"
    max_tokens: int = 1024

    # Retrieval
    chunk_size: int = 900  # characters per chunk (approximate)
    chunk_overlap: int = 150
    top_k: int = 4  # number of chunks fed to the model per question

    # Server
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def is_llm_configured(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
