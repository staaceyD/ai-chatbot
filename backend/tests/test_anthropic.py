import json
from collections.abc import Callable

import httpx2 as httpx
import pytest

from interview_bot.llm import LLMError
from interview_bot.llm.anthropic import JSON_ONLY, AnthropicClient

Handler = Callable[[httpx.Request], httpx.Response]


def client_with(handler: Handler, *, max_tokens: int = 4096) -> AnthropicClient:
    return AnthropicClient(
        model="claude-haiku-4-5",
        max_tokens=max_tokens,
        timeout_seconds=5.0,
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )


def message(text: str, *, stop_reason: str = "end_turn") -> dict:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-4-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


def capturing(response: httpx.Response) -> tuple[Handler, dict]:
    sent: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.read()))
        return response

    return handler, sent


async def test_sends_prompt_and_returns_the_reply() -> None:
    handler, sent = capturing(httpx.Response(200, json=message("42")))
    client = client_with(handler)

    reply = await client.complete(system="be brief", prompt="what is 6*7?")

    assert reply == "42"
    assert sent["model"] == "claude-haiku-4-5"
    assert sent["max_tokens"] == 4096
    assert sent["system"] == "be brief"
    assert sent["messages"] == [{"role": "user", "content": "what is 6*7?"}]
    await client.aclose()


async def test_json_mode_asks_for_json_in_the_system_prompt() -> None:
    handler, sent = capturing(httpx.Response(200, json=message("{}")))
    client = client_with(handler)

    await client.complete(system="be brief", prompt="p", json_mode=True)

    assert sent["system"] == f"be brief\n\n{JSON_ONLY}"
    await client.aclose()


async def test_joins_several_text_blocks() -> None:
    reply = message("")
    reply["content"] = [{"type": "text", "text": '{"a":'}, {"type": "text", "text": " 1}"}]
    client = client_with(lambda request: httpx.Response(200, json=reply))

    assert await client.complete(system="s", prompt="p") == '{"a": 1}'
    await client.aclose()


async def test_api_error_becomes_llm_error() -> None:
    client = client_with(
        lambda request: httpx.Response(
            400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "no"}}
        )
    )

    with pytest.raises(LLMError, match="400"):
        await client.complete(system="s", prompt="p")
    await client.aclose()


async def test_unreachable_api_becomes_llm_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = client_with(handler)

    with pytest.raises(LLMError, match="Could not reach the Anthropic API"):
        await client.complete(system="s", prompt="p")
    await client.aclose()


async def test_truncated_reply_becomes_llm_error() -> None:
    client = client_with(
        lambda request: httpx.Response(200, json=message('{"half', stop_reason="max_tokens")),
        max_tokens=16,
    )

    with pytest.raises(LLMError, match="cut off"):
        await client.complete(system="s", prompt="p")
    await client.aclose()


async def test_refusal_becomes_llm_error() -> None:
    client = client_with(
        lambda request: httpx.Response(200, json=message("", stop_reason="refusal"))
    )

    with pytest.raises(LLMError, match="declined"):
        await client.complete(system="s", prompt="p")
    await client.aclose()


async def test_empty_reply_becomes_llm_error() -> None:
    client = client_with(lambda request: httpx.Response(200, json=message("")))

    with pytest.raises(LLMError, match="empty"):
        await client.complete(system="s", prompt="p")
    await client.aclose()


async def test_missing_credentials_becomes_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = client_with(lambda request: httpx.Response(200, json=message("{}")))

    async def unauthenticated(**kwargs: object) -> None:
        # The SDK raises a plain TypeError when it cannot resolve a key.
        raise TypeError("Could not resolve authentication method")

    monkeypatch.setattr(client._client.messages, "create", unauthenticated)

    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
        await client.complete(system="s", prompt="p")
    await client.aclose()
