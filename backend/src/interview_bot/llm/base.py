from typing import Protocol, runtime_checkable


class LLMError(RuntimeError):
    """A backend could not produce a completion."""


@runtime_checkable
class LLMClient(Protocol):
    """The only thing the rest of the app knows about a model provider."""

    name: str
    model: str

    async def complete(self, *, system: str, prompt: str, json_mode: bool = False) -> str:
        """Return the model's reply. With json_mode, the reply is a JSON document."""
        ...

    async def aclose(self) -> None: ...
