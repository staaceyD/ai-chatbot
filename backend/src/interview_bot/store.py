from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from interview_bot.domain import Difficulty, Question, Topic


@dataclass
class Session:
    id: str
    topic: Topic
    difficulty: Difficulty
    questions: dict[str, Question] = field(default_factory=dict)

    @property
    def asked_prompts(self) -> list[str]:
        return [question.prompt for question in self.questions.values()]


class SessionStore(Protocol):
    """Async so a database-backed store can replace this without touching callers."""

    async def create(self, *, topic: Topic, difficulty: Difficulty) -> Session: ...

    async def get(self, session_id: str) -> Session | None: ...

    async def add_question(self, session_id: str, question: Question) -> None: ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def create(self, *, topic: Topic, difficulty: Difficulty) -> Session:
        session = Session(id=str(uuid4()), topic=topic, difficulty=difficulty)
        self._sessions[session.id] = session
        return session

    async def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def add_question(self, session_id: str, question: Question) -> None:
        self._sessions[session_id].questions[question.id] = question
