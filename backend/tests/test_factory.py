import pytest

from interview_bot.config import Settings
from interview_bot.llm import LLMClient, build_llm_client


async def test_builds_ollama_client_from_settings() -> None:
    client = build_llm_client(Settings(llm_backend="ollama", ollama_model="qwen2.5:7b"))

    assert isinstance(client, LLMClient)
    assert client.name == "ollama"
    assert client.model == "qwen2.5:7b"
    await client.aclose()


async def test_builds_echo_client_from_settings() -> None:
    client = build_llm_client(Settings(llm_backend="echo"))

    assert isinstance(client, LLMClient)
    assert client.name == "echo"
    await client.aclose()


async def test_rejects_unknown_backend() -> None:
    settings = Settings.model_construct(llm_backend="nope")

    with pytest.raises(ValueError, match="nope"):
        build_llm_client(settings)
