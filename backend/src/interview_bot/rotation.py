"""Which of an interview's topics the next question comes from."""

import random
from collections import Counter
from collections.abc import Sequence

from interview_bot.domain import Topic


def next_topic(
    topics: Sequence[Topic],
    asked: Sequence[Topic],
    *,
    rng: random.Random | None = None,
) -> Topic:
    """Pick the topic to ask about next, shuffled rather than in order.

    Random on its own would ask about one topic five times before
    touching another, though, so every topic is asked once before any is asked
    twice: the choice is only among the topics asked least so far, which makes
    the interview a shuffled round of the chosen topics, then another.

    `asked` is the topics of the questions already asked, oldest first. Topics
    no longer in the interview are ignored, so a session read back from a store
    written before the list was narrowed still rotates over what it has now.
    """
    if len(topics) == 1:
        return topics[0]

    asked_counts = Counter(topic for topic in asked if topic in topics)
    fewest = min(asked_counts[topic] for topic in topics)
    due = [topic for topic in topics if asked_counts[topic] == fewest]

    # The topic that closed one round would otherwise be free to open the next,
    # which reads as a repeat however well shuffled the rounds around it are.
    previous = asked[-1] if asked else None
    unrepeated = [topic for topic in due if topic != previous]

    return (rng or random).choice(unrepeated or due)
