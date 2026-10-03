"""Behaviour specific to the SQLite store, beyond the shared contract."""

from pathlib import Path

import aiosqlite
import pytest

from interview_bot.config import Settings
from interview_bot.domain import Difficulty, Grade, Question, Topic
from interview_bot.store import (
    InMemorySessionStore,
    SessionStore,
    SQLiteSessionStore,
    build_session_store,
)


def a_question(prompt: str) -> Question:
    return Question(
        id=prompt,
        topic=Topic.PYTHON,
        difficulty=Difficulty.MID,
        prompt=prompt,
        key_points=["a point"],
    )


async def open_store(path: Path) -> SQLiteSessionStore:
    store = SQLiteSessionStore(path)
    await store.initialize()
    return store


async def test_sessions_survive_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "interview_bot.db"

    first_run = await open_store(path)
    session = await first_run.create(topics=[Topic.REACT], difficulty=Difficulty.SENIOR)
    await first_run.add_question(session.id, a_question("What is the virtual DOM?"))
    await first_run.aclose()

    second_run = await open_store(path)
    loaded = await second_run.get(session.id)
    await second_run.aclose()

    assert loaded is not None
    assert loaded.topics == [Topic.REACT]
    assert loaded.difficulty == Difficulty.SENIOR
    assert loaded.asked_prompts == ["What is the virtual DOM?"]


async def test_reopening_does_not_wipe_existing_data(tmp_path: Path) -> None:
    path = tmp_path / "interview_bot.db"

    first_run = await open_store(path)
    session = await first_run.create(topics=[Topic.PYTHON], difficulty=Difficulty.MID)
    await first_run.add_question(session.id, a_question("first"))
    await first_run.aclose()

    second_run = await open_store(path)
    await second_run.add_question(session.id, a_question("second"))
    loaded = await second_run.get(session.id)
    await second_run.aclose()

    assert loaded.asked_prompts == ["first", "second"]


async def test_grades_survive_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "interview_bot.db"

    first_run = await open_store(path)
    session = await first_run.create(topics=[Topic.PYTHON], difficulty=Difficulty.MID)
    await first_run.add_question(session.id, a_question("What is the GIL?"))
    await first_run.record_grade(
        session.id, "What is the GIL?", Grade(score=4, verdict="Good answer.")
    )
    await first_run.aclose()

    second_run = await open_store(path)
    loaded = await second_run.get(session.id)
    await second_run.aclose()

    assert loaded.latest_grade == Grade(score=4, verdict="Good answer.")


async def test_a_grade_needs_an_existing_question(tmp_path: Path) -> None:
    store = await open_store(tmp_path / "interview_bot.db")
    session = await store.create(topics=[Topic.PYTHON], difficulty=Difficulty.MID)

    with pytest.raises(Exception, match="FOREIGN KEY"):
        await store.record_grade(session.id, "no-such-question", Grade(score=1, verdict="?"))

    await store.aclose()


async def test_creates_the_database_file(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "interview_bot.db"

    store = await open_store(path)
    await store.create(topics=[Topic.PYTHON], difficulty=Difficulty.MID)
    await store.aclose()

    assert path.exists()


async def test_a_question_needs_an_existing_session(tmp_path: Path) -> None:
    store = await open_store(tmp_path / "interview_bot.db")

    with pytest.raises(Exception, match="FOREIGN KEY"):
        await store.add_question("no-such-session", a_question("orphan"))

    await store.aclose()


async def test_using_the_store_before_initialize_is_an_error(tmp_path: Path) -> None:
    store = SQLiteSessionStore(tmp_path / "interview_bot.db")

    with pytest.raises(RuntimeError, match="before initialize"):
        await store.get("anything")


async def test_factory_builds_the_configured_store(tmp_path: Path) -> None:
    sqlite_store: SessionStore = build_session_store(
        Settings(store_backend="sqlite", sqlite_path=tmp_path / "x.db")
    )
    memory_store: SessionStore = build_session_store(Settings(store_backend="memory"))

    assert isinstance(sqlite_store, SQLiteSessionStore)
    assert isinstance(memory_store, InMemorySessionStore)


async def test_factory_rejects_an_unknown_backend() -> None:
    settings = Settings.model_construct(store_backend="postgres")

    with pytest.raises(ValueError, match="postgres"):
        build_session_store(settings)


async def test_a_file_from_before_the_model_column_still_opens(tmp_path: Path) -> None:
    """The migration a file written before the choice existed needs."""
    path = tmp_path / "interview_bot.db"
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "CREATE TABLE sessions ("
            " id TEXT PRIMARY KEY, topic TEXT NOT NULL, difficulty TEXT NOT NULL)"
        )
        await db.execute(
            "INSERT INTO sessions (id, topic, difficulty) VALUES ('old', 'python', 'mid')"
        )
        await db.commit()

    store = await open_store(path)
    loaded = await store.get("old")
    await store.aclose()

    assert loaded is not None
    assert loaded.topics == [Topic.PYTHON]
    # An interview started before there was a choice runs on the local model.
    assert loaded.model_provider == "ollama"


async def test_a_file_from_before_mixed_topics_still_opens(tmp_path: Path) -> None:
    """The migration a file written while a session had one topic needs."""
    path = tmp_path / "interview_bot.db"
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "CREATE TABLE sessions ("
            " id TEXT PRIMARY KEY, topic TEXT NOT NULL, difficulty TEXT NOT NULL,"
            " model_provider TEXT NOT NULL DEFAULT 'ollama')"
        )
        await db.execute(
            "INSERT INTO sessions (id, topic, difficulty) VALUES ('old', 'react', 'senior')"
        )
        await db.commit()

    store = await open_store(path)
    loaded = await store.get("old")
    # A session from before the list existed still takes new questions.
    await store.add_question("old", a_question("What is the virtual DOM?"))
    await store.aclose()

    assert loaded is not None
    # The one topic it was started on, now as the only topic it covers.
    assert loaded.topics == [Topic.REACT]
    assert loaded.difficulty == Difficulty.SENIOR


async def test_a_file_that_called_the_column_backend_still_opens(tmp_path: Path) -> None:
    """The migration a file written while the column had its old name needs."""
    path = tmp_path / "interview_bot.db"
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "CREATE TABLE sessions ("
            " id TEXT PRIMARY KEY, topic TEXT NOT NULL, difficulty TEXT NOT NULL,"
            " backend TEXT NOT NULL DEFAULT 'ollama')"
        )
        await db.execute(
            "INSERT INTO sessions (id, topic, difficulty, backend)"
            " VALUES ('old', 'python', 'mid', 'anthropic')"
        )
        await db.commit()

    store = await open_store(path)
    loaded = await store.get("old")
    await store.aclose()

    assert loaded is not None
    # Renamed rather than added, so the interview keeps the model it was on.
    assert loaded.model_provider == "anthropic"
