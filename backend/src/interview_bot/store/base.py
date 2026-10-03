from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from interview_bot.domain import Difficulty, Explanation, Grade, Question, Topic

# What a session runs on when nobody chose, mirroring the settings default.
DEFAULT_MODEL_PROVIDER = "ollama"


@dataclass
class Session:
    id: str
    topics: list[Topic]
    difficulty: Difficulty
    # The model provider this interview uses. Stored per session so a resume
    # comes back on the model it was running on, and so switching model is a
    # change to the interview rather than to the whole app.
    model_provider: str = DEFAULT_MODEL_PROVIDER
    questions: dict[str, Question] = field(default_factory=dict)
    grades: dict[str, Grade] = field(default_factory=dict)
    explanations: dict[str, Explanation] = field(default_factory=dict)

    @property
    def asked_prompts(self) -> list[str]:
        return [question.prompt for question in self.questions.values()]

    @property
    def asked_topics(self) -> list[Topic]:
        """The topic of each question asked so far, oldest first."""
        return [question.topic for question in self.questions.values()]

    @property
    def latest_question(self) -> Question | None:
        """The question to return to when an interview is resumed."""
        return next(reversed(self.questions.values()), None)

    @property
    def latest_grade(self) -> Grade | None:
        """The grade for `latest_question`, so a resume does not re-ask it."""
        current = self.latest_question
        return self.grades.get(current.id) if current else None

    @property
    def latest_explanation(self) -> Explanation | None:
        """The worked answer for `latest_question`, so a resume does not regenerate it.

        Withheld until the question is graded. A worked answer written ahead is
        in the store before the candidate has attempted anything, and handing
        that back would turn a refresh into a way to read the answer instead.
        """
        current = self.latest_question
        if current is None or current.id not in self.grades:
            return None
        return self.explanations.get(current.id)


def new_session_id() -> str:
    return str(uuid4())


class SessionStore(Protocol):
    """Async so a database-backed store can replace the in-memory one."""

    async def initialize(self) -> None: ...

    async def create(
        self,
        *,
        topics: list[Topic],
        difficulty: Difficulty,
        model_provider: str = DEFAULT_MODEL_PROVIDER,
    ) -> Session: ...

    async def get(self, session_id: str) -> Session | None: ...

    async def set_model_provider(self, session_id: str, model_provider: str) -> None: ...

    async def add_question(self, session_id: str, question: Question) -> None: ...

    async def record_grade(self, session_id: str, question_id: str, grade: Grade) -> None: ...

    async def record_explanation(
        self, session_id: str, question_id: str, explanation: Explanation
    ) -> None: ...

    async def aclose(self) -> None: ...
