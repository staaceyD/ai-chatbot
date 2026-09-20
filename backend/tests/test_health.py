from httpx import AsyncClient


async def test_health_reports_the_active_backend(api: AsyncClient) -> None:
    response = await api.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "llm": {"backend": "echo", "model": "echo"}}
