from interview_bot.config import Settings
from interview_bot.store.base import SessionStore
from interview_bot.store.memory import InMemorySessionStore
from interview_bot.store.sqlite import SQLiteSessionStore


def build_session_store(settings: Settings) -> SessionStore:
    if settings.store_backend == "sqlite":
        return SQLiteSessionStore(settings.sqlite_path)
    if settings.store_backend == "memory":
        return InMemorySessionStore()
    raise ValueError(f"Unknown store backend: {settings.store_backend}")
