from interview_bot.domain import Difficulty, Question, Topic
from interview_bot.store import InMemorySessionStore


def a_question(prompt: str) -> Question:
    return Question(
        id=prompt,
        topic=Topic.PYTHON,
        difficulty=Difficulty.MID,
        prompt=prompt,
        key_points=["point"],
    )


async def test_created_session_can_be_read_back(store: InMemorySessionStore) -> None:
    session = await store.create(topic=Topic.REACT, difficulty=Difficulty.SENIOR)

    assert await store.get(session.id) == session
    assert session.topic == Topic.REACT
    assert session.difficulty == Difficulty.SENIOR


async def test_unknown_session_is_none(store: InMemorySessionStore) -> None:
    assert await store.get("nope") is None


async def test_sessions_are_isolated(store: InMemorySessionStore) -> None:
    first = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    second = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    await store.add_question(first.id, a_question("only in first"))

    assert first.id != second.id
    assert (await store.get(second.id)).questions == {}


async def test_asked_prompts_accumulate(store: InMemorySessionStore) -> None:
    session = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    await store.add_question(session.id, a_question("first"))
    await store.add_question(session.id, a_question("second"))

    assert (await store.get(session.id)).asked_prompts == ["first", "second"]
