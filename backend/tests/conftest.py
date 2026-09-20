import pytest
from httpx import ASGITransport, AsyncClient

from interview_bot.config import Settings
from interview_bot.llm.echo import EchoClient
from interview_bot.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(llm_backend="echo")


@pytest.fixture
async def api(settings: Settings):
    app = create_app(settings=settings, llm_client=EchoClient())
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client
