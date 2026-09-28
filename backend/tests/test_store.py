"""The contract every SessionStore must satisfy, run against each implementation."""

from collections.abc import AsyncIterator

import pytest

from interview_bot.domain import Difficulty, Explanation, Grade, Question, Topic
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


async def test_grade_round_trips_with_its_question(store: SessionStore) -> None:
    session = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    await store.add_question(session.id, a_question("What is the GIL?"))
    grade = Grade(score=4, verdict="Good answer.", covered=["a mutex"], missed=["I/O"])

    await store.record_grade(session.id, "What is the GIL?", grade)

    loaded = await store.get(session.id)
    assert loaded.grades == {"What is the GIL?": grade}
    assert loaded.latest_grade == grade


async def test_regrading_replaces_the_previous_grade(store: SessionStore) -> None:
    session = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    await store.add_question(session.id, a_question("q"))

    await store.record_grade(session.id, "q", Grade(score=1, verdict="Thin."))
    await store.record_grade(session.id, "q", Grade(score=5, verdict="Much better."))

    assert (await store.get(session.id)).latest_grade.score == 5


async def test_an_unanswered_latest_question_has_no_grade(store: SessionStore) -> None:
    session = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    await store.add_question(session.id, a_question("first"))
    await store.record_grade(session.id, "first", Grade(score=3, verdict="Fine."))
    await store.add_question(session.id, a_question("second"))

    assert (await store.get(session.id)).latest_grade is None


async def test_explanation_round_trips_with_its_question(store: SessionStore) -> None:
    session = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    await store.add_question(session.id, a_question("What is the GIL?"))
    explanation = Explanation(
        answer="A mutex around the interpreter.",
        points=[{"point": "a mutex", "detail": "It guards interpreter state."}],
        pitfalls=["Reaching for threads on CPU-bound work"],
    )

    await store.record_explanation(session.id, "What is the GIL?", explanation)

    loaded = await store.get(session.id)
    assert loaded.explanations == {"What is the GIL?": explanation}
    assert loaded.latest_explanation == explanation


async def test_an_unexplained_latest_question_has_no_explanation(store: SessionStore) -> None:
    session = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    await store.add_question(session.id, a_question("first"))
    await store.record_explanation(session.id, "first", Explanation(answer="Because."))
    await store.add_question(session.id, a_question("second"))

    assert (await store.get(session.id)).latest_explanation is None
