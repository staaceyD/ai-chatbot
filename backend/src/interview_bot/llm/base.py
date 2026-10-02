from typing import Protocol, runtime_checkable


class LLMError(RuntimeError):
    """A model provider could not produce a completion."""


@runtime_checkable
class LLMClient(Protocol):
    """The only thing the rest of the app knows about a model provider."""

    name: str
    model: str

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        json_mode: bool = False,
        timeout_seconds: float | None = None,
    ) -> str:
        """Return the model's reply. With json_mode, the reply is a JSON document.

        `timeout_seconds` overrides the client's own timeout for one call, for
        the request that is expected to take far longer than the rest.
        """
        ...

    async def aclose(self) -> None: ...
