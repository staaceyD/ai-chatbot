import json
from collections.abc import Callable

import httpx
import pytest

from interview_bot.llm import LLMError
from interview_bot.llm.ollama import OllamaClient

Handler = Callable[[httpx.Request], httpx.Response]


def client_with(handler: Handler) -> OllamaClient:
    return OllamaClient(
        base_url="http://ollama.test",
        model="llama3.1:8b",
        timeout_seconds=5.0,
        transport=httpx.MockTransport(handler),
    )


def capturing(response: httpx.Response) -> tuple[Handler, dict]:
    sent: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.read()))
        return response

    return handler, sent


async def test_sends_prompt_and_returns_the_response() -> None:
    handler, sent = capturing(httpx.Response(200, json={"response": "42"}))
    client = client_with(handler)

    reply = await client.complete(system="be brief", prompt="what is 6*7?")

    assert reply == "42"
    assert sent["model"] == "llama3.1:8b"
    assert sent["system"] == "be brief"
    assert sent["prompt"] == "what is 6*7?"
    assert sent["stream"] is False
    assert "format" not in sent
    await client.aclose()


async def test_json_mode_asks_ollama_for_json() -> None:
    handler, sent = capturing(httpx.Response(200, json={"response": "{}"}))
    client = client_with(handler)

    await client.complete(system="s", prompt="p", json_mode=True)

    assert sent["format"] == "json"
    await client.aclose()


async def test_http_error_becomes_llm_error() -> None:
    client = client_with(lambda request: httpx.Response(500, text="boom"))

    with pytest.raises(LLMError, match="500"):
        await client.complete(system="s", prompt="p")
    await client.aclose()


async def test_unreachable_server_becomes_llm_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = client_with(handler)

    with pytest.raises(LLMError, match="Could not reach Ollama"):
        await client.complete(system="s", prompt="p")
    await client.aclose()


async def test_empty_response_becomes_llm_error() -> None:
    client = client_with(lambda request: httpx.Response(200, json={"response": ""}))

    with pytest.raises(LLMError, match="empty"):
        await client.complete(system="s", prompt="p")
    await client.aclose()
