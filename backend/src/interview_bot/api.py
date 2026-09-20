from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from pydantic import AfterValidator, BaseModel, Field

from interview_bot.deps import InterviewerDep, SessionStoreDep
from interview_bot.domain import Difficulty, Grade, Topic

router = APIRouter()


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


class AnswerRequest(BaseModel):
    question_id: str
    answer: Answer


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def start_session(body: StartSessionRequest, store: SessionStoreDep) -> SessionResponse:
    session = await store.create(topic=body.topic, difficulty=body.difficulty)
    return SessionResponse(
        session_id=session.id,
        topic=session.topic,
        difficulty=session.difficulty,
    )


@router.post("/sessions/{session_id}/questions", status_code=status.HTTP_201_CREATED)
async def next_question(
    session_id: str,
    store: SessionStoreDep,
    interviewer: InterviewerDep,
) -> QuestionResponse:
    session = await store.get(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown session")

    question = await interviewer.generate_question(
        topic=session.topic,
        difficulty=session.difficulty,
        avoid=session.asked_prompts,
    )
    await store.add_question(session.id, question)
    return QuestionResponse(
        question_id=question.id,
        prompt=question.prompt,
        topic=question.topic,
        difficulty=question.difficulty,
    )


@router.post("/sessions/{session_id}/answers")
async def submit_answer(
    session_id: str,
    body: AnswerRequest,
    store: SessionStoreDep,
    interviewer: InterviewerDep,
) -> Grade:
    session = await store.get(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown session")

    question = session.questions.get(body.question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown question for this session")

    return await interviewer.grade(question=question, answer=body.answer)
