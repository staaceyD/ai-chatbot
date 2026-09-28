import asyncio
from collections.abc import AsyncIterator
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
    moment a question or a grade needs the model, and started again afterwards.
    """

    def __init__(
        self,
        interviewer: Interviewer,
        store: SessionStore,
        *,
        prefetch: bool = True,
    ) -> None:
        self._interviewer = interviewer
        self._store = store
        self._prefetch = prefetch
        # One question per session is worth writing ahead: the one on screen.
        self._writing: dict[str, _Writing] = {}
        self._waiting_on_the_model = 0

    def prefetch(self, session_id: str, question: Question) -> None:
        """Begin writing the worked answer for a question nobody has asked about yet."""
        if not self._prefetch or self._waiting_on_the_model:
            return
        self._start(session_id, question, prefetch=True)

    async def explain(self, session_id: str, question: Question) -> Explanation:
        """The worked answer, waiting on a prefetch already under way if there is one."""
        writing = self._writing.get(session_id)
        if writing is None or writing.question_id != question.id:
            writing = self._start(session_id, question, prefetch=False)
        writing.prefetch = False
        return await writing.task

    @asynccontextmanager
    async def foreground(self) -> AsyncIterator[None]:
        """Hold the model for work someone is waiting on, dropping any prefetch."""
        self._waiting_on_the_model += 1
        try:
            await self._drop_prefetches()
            yield
        finally:
            self._waiting_on_the_model -= 1

    async def aclose(self) -> None:
        await self._drop_prefetches()

    def _start(self, session_id: str, question: Question, *, prefetch: bool) -> _Writing:
        writing = self._writing.get(session_id)
        if writing is not None and writing.question_id == question.id:
            return writing

        # The candidate has moved on to another question, so the old one is
        # nobody's answer any more.
        self._cancel(writing)

        task = asyncio.create_task(self._write(session_id, question))
        # Nothing ever awaits a prefetch that is not asked for, so read its
        # outcome here: an unretrieved failure surfaces as a stray warning.
        task.add_done_callback(_retrieve)

        started = _Writing(question_id=question.id, task=task, prefetch=prefetch)
        self._writing[session_id] = started
        return started

    async def _write(self, session_id: str, question: Question) -> Explanation:
        try:
            explanation = await self._interviewer.explain(question=question)
            await self._store.record_explanation(session_id, question.id, explanation)
        except BaseException:
            # A write that failed or was cancelled is not this question's answer,
            # so forget it and let the next request start over.
            self._forget(session_id, question.id)
            raise
        return explanation

    async def _drop_prefetches(self) -> None:
        dropped = [writing for writing in self._writing.values() if writing.prefetch]
        for writing in dropped:
            self._cancel(writing)
        if dropped:
            # Wait for the model to actually let go before taking it over.
            await asyncio.gather(*(writing.task for writing in dropped), return_exceptions=True)

    def _cancel(self, writing: _Writing | None) -> None:
        if writing is not None and not writing.task.done():
            writing.task.cancel()

    def _forget(self, session_id: str, question_id: str) -> None:
        writing = self._writing.get(session_id)
        if writing is not None and writing.question_id == question_id:
            del self._writing[session_id]


def _retrieve(task: "asyncio.Task[Explanation]") -> None:
    if not task.cancelled():
        task.exception()
