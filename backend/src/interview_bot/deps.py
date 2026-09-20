from typing import Annotated

from fastapi import Depends, Request

from interview_bot.config import Settings, get_settings
from interview_bot.llm import LLMClient


def get_llm_client(request: Request) -> LLMClient:
    return request.app.state.llm_client


LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
