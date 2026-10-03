"""Interviewing on several topics at once, the way a real interview does."""

from httpx import AsyncClient

from interview_bot.llm.echo import EchoClient
from replies import question_reply

MIXED = ["python", "databases", "algorithms"]


async def start_mixed(api: AsyncClient, topics: list[str] = MIXED) -> str:
    response = await api.post("/sessions", json={"topics": topics, "difficulty": "mid"})
    assert response.status_code == 201
    return response.json()["session_id"]


async def ask(api: AsyncClient, session_id: str, count: int) -> list[str]:
    """The topic each of `count` questions came from."""
    topics = []
    for _ in range(count):
        response = await api.post(f"/sessions/{session_id}/questions")
        assert response.status_code == 201
        topics.append(response.json()["topic"])
    return topics


async def test_a_session_keeps_every_topic_it_was_given(api: AsyncClient) -> None:
    response = await api.post("/sessions", json={"topics": MIXED})

    assert response.json()["topics"] == MIXED


async def test_the_same_topic_twice_is_only_kept_once(api: AsyncClient) -> None:
    """Keeping it twice would quietly weight the rotation towards it."""
    response = await api.post("/sessions", json={"topics": ["python", "react", "python"]})

    assert response.json()["topics"] == ["python", "react"]


async def test_an_interview_needs_at_least_one_topic(api: AsyncClient) -> None:
    response = await api.post("/sessions", json={"topics": []})

    assert response.status_code == 422


async def test_questions_rotate_over_all_the_chosen_topics(
    api: AsyncClient, llm: EchoClient
) -> None:
    llm.queue(*[question_reply(f"question {index}") for index in range(len(MIXED))])
    session_id = await start_mixed(api)

    asked = await ask(api, session_id, len(MIXED))

    assert sorted(asked) == sorted(MIXED)


async def test_each_question_is_tagged_with_the_topic_it_came_from(
    api: AsyncClient, llm: EchoClient
) -> None:
    """The tag is the only thing on screen saying which subject just came up."""
    llm.queue(question_reply("first"), question_reply("second"))
    session_id = await start_mixed(api, ["python", "security"])

    asked = await ask(api, session_id, 2)

    assert set(asked) == {"python", "security"}


async def test_the_generator_is_asked_about_one_topic_at_a_time(
    api: AsyncClient, llm: EchoClient
) -> None:
    """A prompt naming every topic at once would blur them into a generic question."""
    llm.queue(question_reply("first"), question_reply("second"))
    session_id = await start_mixed(api, ["python", "databases"])

    await ask(api, session_id, 2)

    prompts = [call["prompt"] for call in llm.calls]
    assert [("Python" in prompt, "databases and SQL" in prompt) for prompt in prompts] in (
        [(True, False), (False, True)],
        [(False, True), (True, False)],
    )


async def test_a_resumed_interview_still_covers_every_topic(
    api: AsyncClient, llm: EchoClient
) -> None:
    llm.queue(question_reply())
    session_id = await start_mixed(api)
    await ask(api, session_id, 1)

    resumed = await api.get(f"/sessions/{session_id}")

    assert resumed.json()["topics"] == MIXED


async def test_a_single_topic_interview_stays_on_it(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue(*[question_reply(f"question {index}") for index in range(3)])
    session_id = await start_mixed(api, ["react"])

    assert await ask(api, session_id, 3) == ["react"] * 3
