from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LLMBackend = Literal["ollama", "echo"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INTERVIEW_BOT_", env_file=".env")

    llm_backend: LLMBackend = "ollama"
    llm_timeout_seconds: float = 120.0

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b-instruct"

    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
