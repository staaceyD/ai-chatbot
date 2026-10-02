import asyncio
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from interview_bot.domain import Explanation, Question
from interview_bot.interviewer import Interviewer
from interview_bot.store import SessionStore


@dataclass
class _Writing:
    question_id: str
    task: "asyncio.Task[Explanation]"
    # False once somebody is waiting on the result, which makes it foreground
    # work that must not be cancelled out from under them.
    prefetch: bool


class Explainer:
    """Writes worked answers before the candidate asks for one.

    A worked answer is the longest thing the model writes, so leaving it until
    the "Learn more" click means waiting through all of it. There is idle time
    to spend instead: the model has nothing to do while the candidate reads a
    question and types an answer.

    A local model serves one request at a time, though, so writing ahead is only
    free while nobody is waiting. Every prefetch is therefore cancelled the
    moment a question, a grade, or an answer somebody clicked through to needs
    the model, and started again afterwards. Writing that somebody is waiting
    on is never cancelled in turn: it is their request.

    Which model to write with is decided per session, so the interviewer comes
    in with each request rather than being held here.
    """

    def __init__(
        self,
        store: SessionStore,
        *,
        prefetch: bool = True,
    ) -> None:
        self._store = store
        self._prefetch = prefetch
        # One question per session is worth writing ahead: the one on screen.
        self._writing: dict[str, _Writing] = {}
        self._waiting_on_the_model = 0

    def prefetch(self, session_id: str, question: Question, interviewer: Interviewer) -> None:
        """Begin writing the worked answer for a question nobody has asked about yet."""
        if not self._prefetch or self._waiting_on_the_model:
            return
        self._start(session_id, question, interviewer, prefetch=True)

    async def explain(
        self, session_id: str, question: Question, interviewer: Interviewer
    ) -> Explanation:
        """The worked answer, waiting on a prefetch already under way if there is one."""
        writing = self._writing.get(session_id)
        if writing is None or writing.question_id != question.id:
            writing = self._start(session_id, question, interviewer, prefetch=False)
        # Marked before the model is held, so `foreground` leaves alone the very
        # write that is being waited on.
        writing.prefetch = False
        async with self.foreground():
            # Shielded because the task is shared: a client that gives up
            # halfway must not cancel work the store and other waiters are
            # counting on, only stop waiting for it.
            return await asyncio.shield(writing.task)

    @asynccontextmanager
    async def foreground(self) -> AsyncGenerator[None]:
        """Hold the model for work someone is waiting on, dropping any prefetch."""
        self._waiting_on_the_model += 1
        try:
            await self._drop_prefetches()
            yield
        finally:
            self._waiting_on_the_model -= 1

    async def forget(self, session_id: str) -> None:
        """Drop a worked answer being written ahead for one session.

        Used when the session changes model: the answer in flight is the old
        model's, and nobody has asked for it yet, so it is cheaper to throw it
        away than to serve it later as though it came from the new one. An
        answer somebody is already waiting on is left alone, as everywhere else.
        """
        writing = self._writing.get(session_id)
        if writing is None or not writing.prefetch:
            return
        del self._writing[session_id]
        await self._settle([writing])

    async def aclose(self) -> None:
        """Let go of the model and the store before the app closes them.

        Shutdown cancels even a write somebody is waiting on: their request is
        going away with the server either way, and a task still inside
        `explain` when the LLM client and the store close fails silently
        instead of persisting anything.
        """
        await self._settle(self._writing.values())

    def _start(
        self, session_id: str, question: Question, interviewer: Interviewer, *, prefetch: bool
    ) -> _Writing:
        writing = self._writing.get(session_id)
        if writing is not None and writing.question_id == question.id:
            return writing

        # The candidate has moved on to another question, so the old one is
        # nobody's answer any more.
        self._cancel(writing)

        task = asyncio.create_task(self._write(session_id, question, interviewer))
        # Nothing ever awaits a prefetch that is not asked for, so read its
        # outcome here: an unretrieved failure surfaces as a stray warning.
        task.add_done_callback(_retrieve)

        started = _Writing(question_id=question.id, task=task, prefetch=prefetch)
        self._writing[session_id] = started
        return started

    async def _write(
        self, session_id: str, question: Question, interviewer: Interviewer
    ) -> Explanation:
        try:
            # A finished write is not kept in `_writing`, so the store is what
            # says whether this question has been written out already.
            explanation = await self._written(session_id, question.id)
            if explanation is None:
                explanation = await interviewer.explain(question=question)
                await self._store.record_explanation(session_id, question.id, explanation)
        finally:
            # Nothing is tracked once it is over: on success the store holds the
            # lasting copy, and a write that failed or was cancelled is not this
            # question's answer, so the next request starts it over.
            self._forget(session_id, question.id)
        return explanation

    async def _written(self, session_id: str, question_id: str) -> Explanation | None:
        session = await self._store.get(session_id)
        return session.explanations.get(question_id) if session else None

    async def _drop_prefetches(self) -> None:
        await self._settle([writing for writing in self._writing.values() if writing.prefetch])

    async def _settle(self, writings: Iterable[_Writing]) -> None:
        """Cancel writes and wait for the model to actually let go of them."""
        tasks = [writing.task for writing in writings if not writing.task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _cancel(self, writing: _Writing | None) -> None:
        # Work somebody is waiting on is left to finish, and simply stops being
        # tracked; cancelling it here would fail their request instead.
        if writing is not None and writing.prefetch and not writing.task.done():
            writing.task.cancel()

    def _forget(self, session_id: str, question_id: str) -> None:
        writing = self._writing.get(session_id)
        if writing is not None and writing.question_id == question_id:
            del self._writing[session_id]


def _retrieve(task: "asyncio.Task[Explanation]") -> None:
    if not task.cancelled():
        task.exception()
