import httpx

from .base import LLMError


class OllamaClient:
    """Talks to a locally running Ollama server."""

    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model = model
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
        )

    async def complete(self, *, system: str, prompt: str, json_mode: bool = False) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"

        try:
            response = await self._http.post("/api/generate", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"Ollama returned {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach Ollama: {exc}") from exc

        reply = response.json().get("response")
        if not reply:
            raise LLMError("Ollama returned an empty response")
        return reply

    async def aclose(self) -> None:
        await self._http.aclose()
