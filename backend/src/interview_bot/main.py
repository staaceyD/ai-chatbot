from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from interview_bot.config import Settings, get_settings
from interview_bot.deps import LLMClientDep
from interview_bot.llm import LLMClient, build_llm_client


class LLMInfo(BaseModel):
    backend: str
    model: str


class Health(BaseModel):
    status: str
    llm: LLMInfo


def create_app(
    settings: Settings | None = None,
    llm_client: LLMClient | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.llm_client = llm_client or build_llm_client(settings)
        try:
            yield
        finally:
            await app.state.llm_client.aclose()

    app = FastAPI(title="Interview Bot", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health(client: LLMClientDep) -> Health:
        return Health(status="ok", llm=LLMInfo(backend=client.name, model=client.model))

    return app


app = create_app()
