import pytest

from interview_bot.domain import Difficulty, Topic
from interview_bot.prompts import TOPIC_LABELS, TOPIC_SCOPES, generate_prompt


@pytest.mark.parametrize("topic", list(Topic))
def test_every_topic_is_described_to_the_model(topic: Topic) -> None:
    """A topic the prompts cannot describe would make generation raise at request time."""
    prompt = generate_prompt(topic=topic, difficulty=Difficulty.MID, avoid=[])

    assert TOPIC_LABELS[topic] in prompt
    assert TOPIC_SCOPES[topic] in prompt


def test_scope_keeps_a_question_on_its_own_topic() -> None:
    prompt = generate_prompt(topic=Topic.DATABASES, difficulty=Difficulty.SENIOR, avoid=[])

    assert "databases and SQL" in prompt
    assert "isolation levels" in prompt
    assert "senior engineer" in prompt


@pytest.mark.parametrize("topic", list(Topic))
def test_a_question_allows_one_line_of_code_but_no_implementation(topic: Topic) -> None:
    """Topics like databases need exact syntax; none of them need a coding exercise."""
    prompt = generate_prompt(topic=topic, difficulty=Difficulty.MID, avoid=[])

    assert "one-line snippet" in prompt
    assert "Never ask the candidate to implement" in prompt
