"""The API with prefetching on, as it runs for real."""

import asyncio
from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

from interview_bot.config import Settings
from interview_bot.llm.echo import EchoClient
from interview_bot.store import InMemorySessionStore
from replies import explanation_reply, grade_reply, question_reply


@pytest.fixture
def settings() -> Settings:
    return Settings(llm_backend="echo", prefetch_explanations=True)


async def eventually(ready: Callable[[], Awaitable[bool]]) -> bool:
    """Let the background write run, the way reading a question would."""
    for _ in range(100):
        if await ready():
            return True
        await asyncio.sleep(0)
    return False


def written(store: InMemorySessionStore, session_id: str):
    async def ready() -> bool:
        session = await store.get(session_id)
        return session is not None and session.explanations != {}

    return ready


async def start_session(api: AsyncClient) -> str:
    response = await api.post("/sessions", json={"topic": "python", "difficulty": "mid"})
    return response.json()["session_id"]


async def test_the_answer_is_written_while_the_question_goes_unanswered(
    api: AsyncClient, llm: EchoClient, store: InMemorySessionStore
) -> None:
    llm.queue(question_reply(), explanation_reply("Written ahead."))
    session_id = await start_session(api)

    await api.post(f"/sessions/{session_id}/questions")

    assert await eventually(written(store, session_id))


async def test_learn_more_returns_the_answer_without_asking_again(
    api: AsyncClient, llm: EchoClient, store: InMemorySessionStore
) -> None:
    llm.queue(question_reply(), explanation_reply("Written ahead."), grade_reply())
    session_id = await start_session(api)
    question_id = (await api.post(f"/sessions/{session_id}/questions")).json()["question_id"]
    assert await eventually(written(store, session_id))
    await api.post(
        f"/sessions/{session_id}/answers",
        json={"question_id": question_id, "answer": "It is a mutex."},
    )
    calls_before = len(llm.calls)

    response = await api.post(f"/sessions/{session_id}/questions/{question_id}/explanation")

    assert response.status_code == 200
    assert response.json()["answer"] == "Written ahead."
    assert len(llm.calls) == calls_before


async def test_an_answer_written_ahead_is_still_kept_back_until_the_question_is_answered(
    api: AsyncClient, llm: EchoClient, store: InMemorySessionStore
) -> None:
    llm.queue(question_reply(), explanation_reply("Written ahead."))
    session_id = await start_session(api)
    question_id = (await api.post(f"/sessions/{session_id}/questions")).json()["question_id"]
    assert await eventually(written(store, session_id))

    response = await api.post(f"/sessions/{session_id}/questions/{question_id}/explanation")

    assert response.status_code == 409
    assert "Written ahead." not in response.text


async def test_the_next_question_is_written_ahead_too(
    api: AsyncClient, llm: EchoClient, store: InMemorySessionStore
) -> None:
    llm.queue(
        question_reply("first"),
        explanation_reply("First answer."),
        grade_reply(),
        question_reply("second"),
        explanation_reply("Second answer."),
    )
    session_id = await start_session(api)
    first = (await api.post(f"/sessions/{session_id}/questions")).json()["question_id"]
    assert await eventually(written(store, session_id))
    await api.post(
        f"/sessions/{session_id}/answers",
        json={"question_id": first, "answer": "It is a mutex."},
    )

    second = (await api.post(f"/sessions/{session_id}/questions")).json()["question_id"]

    async def second_written() -> bool:
        return second in (await store.get(session_id)).explanations

    assert await eventually(second_written)
    assert (await store.get(session_id)).explanations[second].answer == "Second answer."
