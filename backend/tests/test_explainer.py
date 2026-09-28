"""The prefetching rules: write ahead, but never while somebody is waiting."""

import asyncio
import json

import pytest

from interview_bot.domain import Difficulty, Question, Topic
from interview_bot.explainer import Explainer
from interview_bot.interviewer import Interviewer
from interview_bot.llm import LLMError
from interview_bot.store import InMemorySessionStore

QUESTION = Question(
    id="q1",
    topic=Topic.PYTHON,
    difficulty=Difficulty.MID,
    prompt="What is the GIL?",
    key_points=["a mutex"],
)

ANOTHER = Question(
    id="q2",
    topic=Topic.PYTHON,
    difficulty=Difficulty.MID,
    prompt="What is a decorator?",
    key_points=["a wrapper"],
)


class GatedClient:
    """Holds each reply until the test lets it through, so timing is decided here."""

    name = "gated"
    model = "gated"

    def __init__(self, *, fails: int = 0) -> None:
        self.started = asyncio.Event()
        self.may_finish = asyncio.Event()
        self.calls = 0
        self.cancelled = 0
        self._fails = fails

    async def complete(self, *, system: str, prompt: str, json_mode: bool = False) -> str:
        self.calls += 1
        self.started.set()
        try:
            await self.may_finish.wait()
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        if self._fails > 0:
            self._fails -= 1
            raise LLMError("backend unavailable")
        return json.dumps({"answer": "It is a mutex.", "points": [], "pitfalls": []})

    def finish(self) -> None:
        self.may_finish.set()

    async def aclose(self) -> None:
        return None


@pytest.fixture
def store() -> InMemorySessionStore:
    return InMemorySessionStore()


@pytest.fixture
def llm() -> GatedClient:
    return GatedClient()


def build(llm: GatedClient, store: InMemorySessionStore, *, prefetch: bool = True) -> Explainer:
    return Explainer(Interviewer(llm), store, prefetch=prefetch)


async def a_session(store: InMemorySessionStore, question: Question = QUESTION) -> str:
    session = await store.create(topic=Topic.PYTHON, difficulty=Difficulty.MID)
    await store.add_question(session.id, question)
    return session.id


async def test_a_prefetched_answer_is_written_to_the_store(
    llm: GatedClient, store: InMemorySessionStore
) -> None:
    explainer = build(llm, store)
    session_id = await a_session(store)

    explainer.prefetch(session_id, QUESTION)
    await llm.started.wait()
    llm.finish()
    explanation = await explainer.explain(session_id, QUESTION)

    assert explanation.answer == "It is a mutex."
    assert (await store.get(session_id)).explanations["q1"] == explanation


async def test_learn_more_waits_on_the_prefetch_instead_of_asking_twice(
    llm: GatedClient, store: InMemorySessionStore
) -> None:
    explainer = build(llm, store)
    session_id = await a_session(store)

    explainer.prefetch(session_id, QUESTION)
    await llm.started.wait()
    asked = asyncio.ensure_future(explainer.explain(session_id, QUESTION))
    llm.finish()

    assert (await asked).answer == "It is a mutex."
    assert llm.calls == 1


async def test_prefetching_the_same_question_twice_writes_it_once(
    llm: GatedClient, store: InMemorySessionStore
) -> None:
    explainer = build(llm, store)
    session_id = await a_session(store)

    explainer.prefetch(session_id, QUESTION)
    await llm.started.wait()
    explainer.prefetch(session_id, QUESTION)
    llm.finish()
    await explainer.explain(session_id, QUESTION)

    assert llm.calls == 1


async def test_foreground_work_takes_the_model_back(
    llm: GatedClient, store: InMemorySessionStore
) -> None:
    explainer = build(llm, store)
    session_id = await a_session(store)

    explainer.prefetch(session_id, QUESTION)
    await llm.started.wait()

    async with explainer.foreground():
        # The prefetch has already let go by the time the block is entered.
        assert llm.cancelled == 1
        assert (await store.get(session_id)).explanations == {}


async def test_nothing_is_prefetched_while_the_model_is_busy(
    llm: GatedClient, store: InMemorySessionStore
) -> None:
    explainer = build(llm, store)
    session_id = await a_session(store)

    async with explainer.foreground():
        explainer.prefetch(session_id, QUESTION)

    assert llm.calls == 0


async def test_a_cancelled_prefetch_is_written_again_on_request(
    llm: GatedClient, store: InMemorySessionStore
) -> None:
    explainer = build(llm, store)
    session_id = await a_session(store)

    explainer.prefetch(session_id, QUESTION)
    await llm.started.wait()
    async with explainer.foreground():
        pass

    llm.finish()
    explanation = await explainer.explain(session_id, QUESTION)

    assert explanation.answer == "It is a mutex."
    assert llm.calls == 2


async def test_moving_to_the_next_question_drops_the_one_behind(
    llm: GatedClient, store: InMemorySessionStore
) -> None:
    explainer = build(llm, store)
    session_id = await a_session(store)
    await store.add_question(session_id, ANOTHER)

    explainer.prefetch(session_id, QUESTION)
    await llm.started.wait()
    explainer.prefetch(session_id, ANOTHER)
    llm.finish()
    await explainer.explain(session_id, ANOTHER)

    assert llm.cancelled == 1
    assert "q1" not in (await store.get(session_id)).explanations


async def test_a_failed_write_is_retried_rather_than_remembered(
    store: InMemorySessionStore,
) -> None:
    llm = GatedClient(fails=1)
    llm.finish()
    explainer = build(llm, store)
    session_id = await a_session(store)

    with pytest.raises(LLMError):
        await explainer.explain(session_id, QUESTION)
    explanation = await explainer.explain(session_id, QUESTION)

    assert explanation.answer == "It is a mutex."
    assert llm.calls == 2


async def test_with_prefetching_off_the_answer_is_written_on_request(
    llm: GatedClient, store: InMemorySessionStore
) -> None:
    explainer = build(llm, store, prefetch=False)
    session_id = await a_session(store)

    explainer.prefetch(session_id, QUESTION)
    assert llm.calls == 0

    llm.finish()
    assert (await explainer.explain(session_id, QUESTION)).answer == "It is a mutex."


async def test_closing_lets_go_of_work_in_flight(
    llm: GatedClient, store: InMemorySessionStore
) -> None:
    explainer = build(llm, store)
    session_id = await a_session(store)

    explainer.prefetch(session_id, QUESTION)
    await llm.started.wait()
    await explainer.aclose()

    assert llm.cancelled == 1
