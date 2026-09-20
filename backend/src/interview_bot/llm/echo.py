import json

from .base import LLMError


class EchoClient:
    """Canned replies so the app runs and is testable without a model."""

    name = "echo"

    def __init__(self, *, model: str = "echo", replies: list[str] | None = None) -> None:
        self.model = model
        self._replies = list(replies or [])
        self.calls: list[dict[str, object]] = []

    async def complete(self, *, system: str, prompt: str, json_mode: bool = False) -> str:
        self.calls.append({"system": system, "prompt": prompt, "json_mode": json_mode})
        if self._replies:
            return self._replies.pop(0)
        if json_mode:
            return json.dumps({"echo": prompt})
        return f"echo: {prompt}"

    async def aclose(self) -> None:
        return None


class FailingClient:
    """Always fails, for exercising error paths."""

    name = "failing"

    def __init__(self, *, model: str = "failing", message: str = "backend unavailable") -> None:
        self.model = model
        self._message = message

    async def complete(self, *, system: str, prompt: str, json_mode: bool = False) -> str:
        raise LLMError(self._message)

    async def aclose(self) -> None:
        return None
