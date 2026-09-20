from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from interview_bot.api import router
from interview_bot.config import Settings, get_settings
from interview_bot.deps import LLMClientDep
from interview_bot.llm import LLMClient, LLMError, build_llm_client
from interview_bot.store import InMemorySessionStore, SessionStore


class LLMInfo(BaseModel):
    backend: str
    model: str


class Health(BaseModel):
    status: str
    llm: LLMInfo


def create_app(
    settings: Settings | None = None,
    llm_client: LLMClient | None = None,
    session_store: SessionStore | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.llm_client = llm_client or build_llm_client(settings)
        app.state.session_store = session_store or InMemorySessionStore()
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

    @app.exception_handler(LLMError)
    async def handle_llm_error(request: Request, exc: LLMError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": f"The model is unavailable: {exc}"},
        )

    @app.get("/health")
    async def health(client: LLMClientDep) -> Health:
        return Health(status="ok", llm=LLMInfo(backend=client.name, model=client.model))

    app.include_router(router)
    return app


app = create_app()
