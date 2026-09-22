"""The contract every SessionStore must satisfy, run against each implementation."""

from collections.abc import AsyncIterator

import pytest

from interview_bot.domain import Difficulty, Question, Topic
from interview_bot.store import InMemorySessionStore, SessionStore, SQLiteSessionStore


@pytest.fixture(params=["memory", "sqlite"])
async def store(request: pytest.FixtureRequest, tmp_path) -> AsyncIterator[SessionStore]:
    built: SessionStore = (
        InMemorySessionStore()
        if request.param == "memory"
        else SQLiteSessionStore(tmp_path / "interview_bot.db")
    )
    await built.initialize()
    yield built
    await built.aclose()


def a_question(prompt: str, key_points: list[str] | None = None) -> Question:
    return Question(
        id=prompt,
        topic=Topic.PYTHON,
        difficulty=Difficulty.MID,
        prompt=prompt,
        key_points=key_points or ["point"],
    )


async def test_created_session_can_be_read_back(store: SessionStore) -> None:
    session = await store.create(topic=Topic.REACT, difficulty=Difficulty.SENIOR)

    loaded = await store.get(session.id)

    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.topic == Topic.REACT
    assert loaded.difficulty == Difficulty.SENIOR


async def test_unknown_session_is_none(store: SessionStore) -> None:
    assert await store.get("nope") is None


async def test_sessions_get_distinct_ids(store: SessionStore) -> None:
    first = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    second = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)

    assert first.id != second.id


async def test_sessions_are_isolated(store: SessionStore) -> None:
    first = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    second = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)

    await store.add_question(first.id, a_question("only in first"))

    assert (await store.get(second.id)).questions == {}


async def test_asked_prompts_keep_insertion_order(store: SessionStore) -> None:
    session = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)

    for prompt in ["first", "second", "third"]:
        await store.add_question(session.id, a_question(prompt))

    assert (await store.get(session.id)).asked_prompts == ["first", "second", "third"]


async def test_question_round_trips_intact(store: SessionStore) -> None:
    session = await store.create(topic=Topic.JAVASCRIPT, difficulty=Difficulty.JUNIOR)
    question = Question(
        id="q1",
        topic=Topic.JAVASCRIPT,
        difficulty=Difficulty.JUNIOR,
        prompt="What is a closure?",
        key_points=["captured scope", "lives past the call", "used for privacy"],
    )

    await store.add_question(session.id, question)

    assert (await store.get(session.id)).questions["q1"] == question
