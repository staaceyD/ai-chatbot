"""How a mixed interview moves between the topics it was given."""

import random
from collections import Counter

import pytest

from interview_bot.domain import Topic
from interview_bot.rotation import next_topic

MIXED = [Topic.PYTHON, Topic.DATABASES, Topic.ALGORITHMS, Topic.SECURITY]


def asked_in_order(topics: list[Topic], count: int, *, seed: int = 0) -> list[Topic]:
    """The topics of `count` questions, as the API would ask for them."""
    rng = random.Random(seed)
    asked: list[Topic] = []
    for _ in range(count):
        asked.append(next_topic(topics, asked, rng=rng))
    return asked


def test_one_topic_is_asked_about_every_time() -> None:
    assert asked_in_order([Topic.PYTHON], 5) == [Topic.PYTHON] * 5


@pytest.mark.parametrize("seed", range(10))
def test_every_topic_comes_up_before_any_comes_up_twice(seed: int) -> None:
    """Random alone would ask four Python questions before touching databases."""
    asked = asked_in_order(MIXED, len(MIXED), seed=seed)

    assert sorted(asked) == sorted(MIXED)


@pytest.mark.parametrize("seed", range(10))
def test_rounds_keep_the_topics_evenly_spread(seed: int) -> None:
    asked = asked_in_order(MIXED, 3 * len(MIXED), seed=seed)

    assert set(Counter(asked).values()) == {3}


@pytest.mark.parametrize("seed", range(10))
def test_no_topic_is_asked_about_twice_in_a_row(seed: int) -> None:
    """Including across the seam between one round and the next."""
    asked = asked_in_order(MIXED, 4 * len(MIXED), seed=seed)

    assert all(earlier != later for earlier, later in zip(asked, asked[1:], strict=False))


def test_the_order_is_shuffled_rather_than_the_order_they_were_picked() -> None:
    """A fixed order would make the interview predictable after the first round."""
    rounds = {tuple(asked_in_order(MIXED, len(MIXED), seed=seed)) for seed in range(20)}

    assert len(rounds) > 1


def test_a_topic_no_longer_in_the_interview_does_not_hold_up_the_rotation() -> None:
    """A session read back from a store can have been asked about more than it now covers."""
    asked = [Topic.REACT, Topic.PYTHON]

    assert next_topic([Topic.PYTHON, Topic.DATABASES], asked) == Topic.DATABASES
