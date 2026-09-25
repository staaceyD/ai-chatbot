from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from interview_bot.domain import Difficulty, Topic


def _non_blank(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


Answer = Annotated[str, Field(max_length=5000), AfterValidator(_non_blank)]


class StartSessionRequest(BaseModel):
    topic: Topic
    difficulty: Difficulty = Difficulty.MID


class SessionResponse(BaseModel):
    session_id: str
    topic: Topic
    difficulty: Difficulty


class QuestionResponse(BaseModel):
    """Deliberately without key_points, so the client cannot read the answer."""

    question_id: str
    prompt: str
    topic: Topic
    difficulty: Difficulty


class SessionStateResponse(BaseModel):
    session_id: str
    topic: Topic
    difficulty: Difficulty
    current_question: QuestionResponse | None


class AnswerRequest(BaseModel):
    question_id: str
    answer: Answer


class LLMInfo(BaseModel):
    backend: str
    model: str


class HealthResponse(BaseModel):
    status: str
    llm: LLMInfo
