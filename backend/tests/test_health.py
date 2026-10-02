from httpx import AsyncClient


async def test_health_reports_the_default_provider(api: AsyncClient) -> None:
    response = await api.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["llm"] == {"model_provider": "echo", "model": "echo"}


async def test_health_lists_what_a_session_can_switch_to(api: AsyncClient) -> None:
    response = await api.get("/health")

    offered = [entry["model_provider"] for entry in response.json()["available"]]

    assert offered == ["ollama", "anthropic", "echo"]
