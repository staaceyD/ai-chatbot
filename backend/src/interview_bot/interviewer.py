import json
import re
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from interview_bot.domain import Difficulty, Grade, Question, Topic
from interview_bot.llm import LLMClient, LLMError
from interview_bot.prompts import (
    GENERATE_SYSTEM,
    GRADE_SYSTEM,
    generate_prompt,
    grade_prompt,
)

# Small local models often wrap JSON in a markdown fence despite being asked not to.
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class GeneratedQuestion(BaseModel):
    question: str = Field(min_length=1)
    key_points: list[str] = Field(min_length=1)


class Interviewer:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def generate_question(
        self,
        *,
        topic: Topic,
        difficulty: Difficulty,
        avoid: list[str] | None = None,
    ) -> Question:
        reply = await self._llm.complete(
            system=GENERATE_SYSTEM,
            prompt=generate_prompt(topic=topic, difficulty=difficulty, avoid=avoid or []),
            json_mode=True,
        )
        generated = _parse(reply, GeneratedQuestion)
        return Question(
            id=str(uuid4()),
            topic=topic,
            difficulty=difficulty,
            prompt=generated.question,
            key_points=generated.key_points,
        )

    async def grade(self, *, question: Question, answer: str) -> Grade:
        reply = await self._llm.complete(
            system=GRADE_SYSTEM,
            prompt=grade_prompt(question=question, answer=answer),
            json_mode=True,
        )
        return _parse(reply, Grade)


def _parse[T: BaseModel](reply: str, model: type[T]) -> T:
    fenced = _FENCE.match(reply)
    payload: Any
    try:
        payload = json.loads(fenced.group(1) if fenced else reply)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model did not return JSON: {reply[:200]}") from exc

    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise LLMError(f"Model returned unusable {model.__name__}: {exc}") from exc
