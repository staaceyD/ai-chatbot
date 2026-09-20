from interview_bot.config import Settings
from interview_bot.llm.base import LLMClient
from interview_bot.llm.echo import EchoClient
from interview_bot.llm.ollama import OllamaClient


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_backend == "ollama":
        return OllamaClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    if settings.llm_backend == "echo":
        return EchoClient()
    raise ValueError(f"Unknown LLM backend: {settings.llm_backend}")
