from fastapi import APIRouter, HTTPException, status

from interview_bot.deps import InterviewerDep, LLMClientDep, SessionStoreDep
from interview_bot.domain import Grade, Question
from interview_bot.schemas import (
    AnswerRequest,
    HealthResponse,
    LLMInfo,
    QuestionResponse,
    SessionResponse,
    SessionStateResponse,
    StartSessionRequest,
)
from interview_bot.store import Session, SessionStore

router = APIRouter()


async def _require_session(store: SessionStore, session_id: str) -> Session:
    session = await store.get(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown session")
    return session


def _as_response(question: Question) -> QuestionResponse:
    return QuestionResponse(
        question_id=question.id,
        prompt=question.prompt,
        topic=question.topic,
        difficulty=question.difficulty,
    )


@router.get("/health")
async def health(client: LLMClientDep) -> HealthResponse:
    return HealthResponse(status="ok", llm=LLMInfo(backend=client.name, model=client.model))


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def start_session(body: StartSessionRequest, store: SessionStoreDep) -> SessionResponse:
    session = await store.create(topic=body.topic, difficulty=body.difficulty)
    return SessionResponse(
        session_id=session.id,
        topic=session.topic,
        difficulty=session.difficulty,
    )


@router.get("/sessions/{session_id}")
async def resume_session(session_id: str, store: SessionStoreDep) -> SessionStateResponse:
    session = await _require_session(store, session_id)
    current = session.latest_question
    return SessionStateResponse(
        session_id=session.id,
        topic=session.topic,
        difficulty=session.difficulty,
        current_question=_as_response(current) if current else None,
    )


@router.post("/sessions/{session_id}/questions", status_code=status.HTTP_201_CREATED)
async def next_question(
    session_id: str,
    store: SessionStoreDep,
    interviewer: InterviewerDep,
) -> QuestionResponse:
    session = await _require_session(store, session_id)

    question = await interviewer.generate_question(
        topic=session.topic,
        difficulty=session.difficulty,
        avoid=session.asked_prompts,
    )
    await store.add_question(session.id, question)
    return _as_response(question)


@router.post("/sessions/{session_id}/answers")
async def submit_answer(
    session_id: str,
    body: AnswerRequest,
    store: SessionStoreDep,
    interviewer: InterviewerDep,
) -> Grade:
    session = await _require_session(store, session_id)

    question = session.questions.get(body.question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown question for this session")

    return await interviewer.grade(question=question, answer=body.answer)
