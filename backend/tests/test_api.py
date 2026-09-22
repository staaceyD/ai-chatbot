import pytest
from httpx import AsyncClient

from interview_bot.llm.echo import EchoClient
from replies import grade_reply, question_reply


async def start_session(api: AsyncClient, topic: str = "python") -> str:
    response = await api.post("/sessions", json={"topic": topic, "difficulty": "mid"})
    assert response.status_code == 201
    return response.json()["session_id"]


async def test_full_interview_round(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue(question_reply("What is the GIL?"), grade_reply(score=4))

    session_id = await start_session(api)

    asked = await api.post(f"/sessions/{session_id}/questions")
    assert asked.status_code == 201
    question = asked.json()
    assert question["prompt"] == "What is the GIL?"
    assert question["topic"] == "python"

    graded = await api.post(
        f"/sessions/{session_id}/answers",
        json={"question_id": question["question_id"], "answer": "It is a mutex."},
    )
    assert graded.status_code == 200
    assert graded.json()["score"] == 4
    assert graded.json()["verdict"]


async def test_question_response_hides_the_key_points(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue(question_reply(key_points=["secret point"]))
    session_id = await start_session(api)

    response = await api.post(f"/sessions/{session_id}/questions")

    assert "key_points" not in response.json()
    assert "secret point" not in response.text


async def test_previous_questions_are_sent_to_the_generator(
    api: AsyncClient, llm: EchoClient
) -> None:
    llm.queue(question_reply("first question"), question_reply("second question"))
    session_id = await start_session(api)

    await api.post(f"/sessions/{session_id}/questions")
    await api.post(f"/sessions/{session_id}/questions")

    assert "first question" in llm.calls[1]["prompt"]


async def test_session_defaults_to_mid_difficulty(api: AsyncClient) -> None:
    response = await api.post("/sessions", json={"topic": "react"})

    assert response.status_code == 201
    assert response.json()["difficulty"] == "mid"


@pytest.mark.parametrize("topic", ["python", "react", "javascript"])
async def test_supported_topics(api: AsyncClient, topic: str) -> None:
    response = await api.post("/sessions", json={"topic": topic})

    assert response.status_code == 201
    assert response.json()["topic"] == topic


async def test_unsupported_topic_is_rejected(api: AsyncClient) -> None:
    response = await api.post("/sessions", json={"topic": "cobol"})

    assert response.status_code == 422


async def test_unknown_session_is_not_found(api: AsyncClient) -> None:
    response = await api.post("/sessions/nope/questions")

    assert response.status_code == 404


async def test_answering_an_unknown_question_is_not_found(api: AsyncClient) -> None:
    session_id = await start_session(api)

    response = await api.post(
        f"/sessions/{session_id}/answers",
        json={"question_id": "nope", "answer": "hello"},
    )

    assert response.status_code == 404


async def test_question_from_another_session_is_not_found(
    api: AsyncClient, llm: EchoClient
) -> None:
    llm.queue(question_reply())
    mine = await start_session(api)
    theirs = await start_session(api)
    question_id = (await api.post(f"/sessions/{mine}/questions")).json()["question_id"]

    response = await api.post(
        f"/sessions/{theirs}/answers",
        json={"question_id": question_id, "answer": "hello"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize("answer", ["", "   ", "\n\t"])
async def test_blank_answers_are_rejected(api: AsyncClient, llm: EchoClient, answer: str) -> None:
    llm.queue(question_reply())
    session_id = await start_session(api)
    question_id = (await api.post(f"/sessions/{session_id}/questions")).json()["question_id"]

    response = await api.post(
        f"/sessions/{session_id}/answers",
        json={"question_id": question_id, "answer": answer},
    )

    assert response.status_code == 422


async def test_model_failure_is_reported_as_bad_gateway(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue("not json at all")
    session_id = await start_session(api)

    response = await api.post(f"/sessions/{session_id}/questions")

    assert response.status_code == 502
    assert "model is unavailable" in response.json()["detail"]
