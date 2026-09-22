from enum import StrEnum

from pydantic import BaseModel, Field


class Topic(StrEnum):
    PYTHON = "python"
    REACT = "react"
    JAVASCRIPT = "javascript"


class Difficulty(StrEnum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"


class Question(BaseModel):
    id: str
    topic: Topic
    difficulty: Difficulty
    prompt: str
    # Generated alongside the question and kept server-side: without a question
    # bank these are the only reference the grader has to score against.
    key_points: list[str]


class Grade(BaseModel):
    score: int = Field(ge=0, le=5)
    verdict: str
    covered: list[str] = []
    missed: list[str] = []
