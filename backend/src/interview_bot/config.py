from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LLMBackend = Literal["ollama", "echo"]
StoreBackend = Literal["sqlite", "memory"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INTERVIEW_BOT_", env_file=".env")

    llm_backend: LLMBackend = "ollama"
    llm_timeout_seconds: float = 120.0
    # A worked answer is several times longer than a question or a grade, so it
    # gets its own budget rather than making a hung model take five minutes to
    # fail on every call.
    llm_explain_timeout_seconds: float = 300.0
    prefetch_explanations: bool = True

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b-instruct"

    store_backend: StoreBackend = "sqlite"
    sqlite_path: Path = Path("interview_bot.db")

    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
