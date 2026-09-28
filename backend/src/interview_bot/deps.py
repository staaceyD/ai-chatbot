from typing import Annotated

from fastapi import Depends, Request

from interview_bot.config import Settings, get_settings
from interview_bot.explainer import Explainer
from interview_bot.interviewer import Interviewer
from interview_bot.llm import LLMClient
from interview_bot.store import SessionStore


def get_llm_client(request: Request) -> LLMClient:
    return request.app.state.llm_client


def get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


def get_explainer(request: Request) -> Explainer:
    return request.app.state.explainer


def get_interviewer(llm: Annotated[LLMClient, Depends(get_llm_client)]) -> Interviewer:
    return Interviewer(llm)


LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]
SessionStoreDep = Annotated[SessionStore, Depends(get_session_store)]
InterviewerDep = Annotated[Interviewer, Depends(get_interviewer)]
ExplainerDep = Annotated[Explainer, Depends(get_explainer)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
