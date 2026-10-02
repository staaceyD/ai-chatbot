import anthropic
import httpx2 as httpx

from interview_bot.llm.base import LLMError

# The API has no schema-less JSON mode: structured outputs want a JSON schema
# per call, which this interface does not carry. The prompts already ask for
# JSON only; this repeats it where the model is most likely to obey it.
JSON_ONLY = "Reply with a single JSON document and nothing else — no prose, no markdown fence."


class AnthropicClient:
    """Talks to a hosted Claude model over the Anthropic API.

    Several times faster than a small model on a laptop, and it answers
    several requests at once, so a worked answer being written ahead costs a
    grade nothing even while both are in flight.
    """

    name = "anthropic"

    def __init__(
        self,
        *,
        model: str,
        max_tokens: int,
        timeout_seconds: float,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model = model
        self._max_tokens = max_tokens
        # Without an explicit key the SDK resolves one itself, from
        # ANTHROPIC_API_KEY or from a profile left by `ant auth login`.
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=timeout_seconds,
            http_client=(
                anthropic.DefaultAsyncHttpxClient(transport=transport) if transport else None
            ),
        )

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        json_mode: bool = False,
        timeout_seconds: float | None = None,
    ) -> str:
        client = self._client
        if timeout_seconds is not None:
            client = client.with_options(timeout=timeout_seconds)

        try:
            # Haiku does not think unless asked to, and rejects an effort level,
            # so neither is set: these are short calls that want neither.
            message = await client.messages.create(
                model=self.model,
                max_tokens=self._max_tokens,
                system=f"{system}\n\n{JSON_ONLY}" if json_mode else system,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIStatusError as exc:
            raise LLMError(f"The Anthropic API returned {exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(f"Could not reach the Anthropic API: {exc}") from exc
        except anthropic.AnthropicError as exc:
            raise LLMError(f"The Anthropic API could not be called: {exc}") from exc
        except TypeError as exc:
            # What the SDK raises when it finds no credentials to use. Left
            # uncaught it reaches the browser as a bare 500 halfway through an
            # interview, which says nothing about the key being missing.
            raise LLMError(f"No Anthropic credentials — set ANTHROPIC_API_KEY ({exc})") from exc

        if message.stop_reason == "refusal":
            raise LLMError("Claude declined to answer")
        if message.stop_reason == "max_tokens":
            raise LLMError(
                f"Claude ran out of room at {self._max_tokens} tokens, so the reply is cut off"
            )

        reply = "".join(block.text for block in message.content if block.type == "text")
        if not reply:
            raise LLMError("Claude returned an empty response")
        return reply

    async def aclose(self) -> None:
        await self._client.close()
