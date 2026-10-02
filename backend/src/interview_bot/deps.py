from collections.abc import Mapping
from typing import Annotated

from fastapi import Depends, Request

from interview_bot.config import Settings
from interview_bot.explainer import Explainer
from interview_bot.interviewer import Interviewer
from interview_bot.llm import LLMClient
from interview_bot.store import SessionStore


def get_settings(request: Request) -> Settings:
    """The settings this app was built with, which a test may have replaced."""
    return request.app.state.settings


def get_llm_clients(request: Request) -> Mapping[str, LLMClient]:
    return request.app.state.llm_clients


def get_interviewers(request: Request) -> Mapping[str, Interviewer]:
    return request.app.state.interviewers


def get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


def get_explainer(request: Request) -> Explainer:
    return request.app.state.explainer


LLMClientsDep = Annotated[Mapping[str, LLMClient], Depends(get_llm_clients)]
InterviewersDep = Annotated[Mapping[str, Interviewer], Depends(get_interviewers)]
SessionStoreDep = Annotated[SessionStore, Depends(get_session_store)]
ExplainerDep = Annotated[Explainer, Depends(get_explainer)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
