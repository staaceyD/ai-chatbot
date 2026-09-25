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

    @property
    def latest_question(self) -> Question | None:
        """The question to return to when an interview is resumed."""
        return next(reversed(self.questions.values()), None)


def new_session_id() -> str:
    return str(uuid4())


class SessionStore(Protocol):
    """Async so a database-backed store can replace the in-memory one."""

    async def initialize(self) -> None: ...

    async def create(self, *, topic: Topic, difficulty: Difficulty) -> Session: ...

    async def get(self, session_id: str) -> Session | None: ...

    async def add_question(self, session_id: str, question: Question) -> None: ...

    async def aclose(self) -> None: ...
