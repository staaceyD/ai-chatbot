from interview_bot.domain import Difficulty, Question, Topic
from interview_bot.store.base import Session, new_session_id


class InMemorySessionStore:
    """Keeps sessions for the life of the process."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def initialize(self) -> None:
        return None

    async def create(self, *, topic: Topic, difficulty: Difficulty) -> Session:
        session = Session(id=new_session_id(), topic=topic, difficulty=difficulty)
        self._sessions[session.id] = session
        return session

    async def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def add_question(self, session_id: str, question: Question) -> None:
        self._sessions[session_id].questions[question.id] = question

    async def aclose(self) -> None:
        return None
