from interview_bot.domain import Difficulty, Explanation, Grade, Question, Topic
from interview_bot.store.base import DEFAULT_MODEL_PROVIDER, Session, new_session_id


class InMemorySessionStore:
    """Keeps sessions for the life of the process."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def initialize(self) -> None:
        return None

    async def create(
        self, *, topic: Topic, difficulty: Difficulty, model_provider: str = DEFAULT_MODEL_PROVIDER
    ) -> Session:
        session = Session(
            id=new_session_id(), topic=topic, difficulty=difficulty, model_provider=model_provider
        )
        self._sessions[session.id] = session
        return session

    async def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def set_model_provider(self, session_id: str, model_provider: str) -> None:
        self._sessions[session_id].model_provider = model_provider

    async def add_question(self, session_id: str, question: Question) -> None:
        self._sessions[session_id].questions[question.id] = question

    async def record_grade(self, session_id: str, question_id: str, grade: Grade) -> None:
        self._sessions[session_id].grades[question_id] = grade

    async def record_explanation(
        self, session_id: str, question_id: str, explanation: Explanation
    ) -> None:
        self._sessions[session_id].explanations[question_id] = explanation

    async def aclose(self) -> None:
        return None
