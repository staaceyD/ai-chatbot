import pytest
from httpx import ASGITransport, AsyncClient

from interview_bot.config import Settings
from interview_bot.llm.echo import EchoClient
from interview_bot.main import create_app
from interview_bot.store import InMemorySessionStore


@pytest.fixture
def settings() -> Settings:
    return Settings(llm_backend="echo")


@pytest.fixture
def llm() -> EchoClient:
    return EchoClient()


@pytest.fixture
def store() -> InMemorySessionStore:
    return InMemorySessionStore()


@pytest.fixture
async def api(settings: Settings, llm: EchoClient, store: InMemorySessionStore):
    app = create_app(settings=settings, llm_client=llm, session_store=store)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client
