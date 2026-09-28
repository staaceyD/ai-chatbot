from fastapi import APIRouter, HTTPException, status

from interview_bot.deps import ExplainerDep, InterviewerDep, LLMClientDep, SessionStoreDep
from interview_bot.domain import Explanation, Grade, Question
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


def _require_question(session: Session, question_id: str) -> Question:
    question = session.questions.get(question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown question for this session")
    return question


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
        current_grade=session.latest_grade,
        current_explanation=session.latest_explanation,
    )


@router.post("/sessions/{session_id}/questions", status_code=status.HTTP_201_CREATED)
async def next_question(
    session_id: str,
    store: SessionStoreDep,
    interviewer: InterviewerDep,
    explainer: ExplainerDep,
) -> QuestionResponse:
    session = await _require_session(store, session_id)

    async with explainer.foreground():
        question = await interviewer.generate_question(
            topic=session.topic,
            difficulty=session.difficulty,
            avoid=session.asked_prompts,
        )
    await store.add_question(session.id, question)

    # The model is free now and stays free while the question is answered
    explainer.prefetch(session.id, question)
    return _as_response(question)


@router.post("/sessions/{session_id}/answers")
async def submit_answer(
    session_id: str,
    body: AnswerRequest,
    store: SessionStoreDep,
    interviewer: InterviewerDep,
    explainer: ExplainerDep,
) -> Grade:
    session = await _require_session(store, session_id)
    question = _require_question(session, body.question_id)

    async with explainer.foreground():
        grade = await interviewer.grade(question=question, answer=body.answer)
    await store.record_grade(session.id, question.id, grade)

    # Picked up again in case answering interrupted it, or the backend restarted
    # between the question and the answer.
    explainer.prefetch(session.id, question)
    return grade


@router.post("/sessions/{session_id}/questions/{question_id}/explanation")
async def explain_question(
    session_id: str,
    question_id: str,
    store: SessionStoreDep,
    explainer: ExplainerDep,
) -> Explanation:
    session = await _require_session(store, session_id)
    question = _require_question(session, question_id)

    if question_id not in session.grades:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Answer the question before reading the explanation"
        )

    explained = session.explanations.get(question_id)
    if explained is not None:
        return explained

    # Written ahead while the question was being answered, in which case this
    # returns as fast as the store can hand it over.
    return await explainer.explain(session.id, question)
