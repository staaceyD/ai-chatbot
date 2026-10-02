import pytest

from interview_bot.config import Settings
from interview_bot.llm import LLMClient, build_llm_client


async def test_builds_ollama_client_from_settings() -> None:
    client = build_llm_client(Settings(default_model_provider="ollama", ollama_model="qwen2.5:7b"))

    assert isinstance(client, LLMClient)
    assert client.name == "ollama"
    assert client.model == "qwen2.5:7b"
    await client.aclose()


async def test_builds_anthropic_client_from_settings() -> None:
    client = build_llm_client(
        Settings(default_model_provider="anthropic", anthropic_model="claude-haiku-4-5")
    )

    assert isinstance(client, LLMClient)
    assert client.name == "anthropic"
    assert client.model == "claude-haiku-4-5"
    await client.aclose()


async def test_builds_echo_client_from_settings() -> None:
    client = build_llm_client(Settings(default_model_provider="echo"))

    assert isinstance(client, LLMClient)
    assert client.name == "echo"
    await client.aclose()


async def test_rejects_unknown_model_provider() -> None:
    settings = Settings.model_construct(default_model_provider="nope")

    with pytest.raises(ValueError, match="nope"):
        build_llm_client(settings)
