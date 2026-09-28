import pytest
from httpx import AsyncClient

from interview_bot.llm.echo import EchoClient
from replies import explanation_reply, grade_reply, question_reply


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


async def test_resume_returns_the_question_in_progress(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue(question_reply("What is the GIL?"))
    session_id = await start_session(api)
    asked = (await api.post(f"/sessions/{session_id}/questions")).json()

    resumed = await api.get(f"/sessions/{session_id}")

    assert resumed.status_code == 200
    assert resumed.json() == {
        "session_id": session_id,
        "topic": "python",
        "difficulty": "mid",
        "current_question": asked,
        "current_grade": None,
        "current_explanation": None,
    }


async def test_resume_returns_the_grade_already_given(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue(question_reply(), grade_reply(score=4, verdict="Good answer."))
    session_id = await start_session(api)
    question_id = (await api.post(f"/sessions/{session_id}/questions")).json()["question_id"]
    await api.post(
        f"/sessions/{session_id}/answers",
        json={"question_id": question_id, "answer": "It is a mutex."},
    )

    resumed = (await api.get(f"/sessions/{session_id}")).json()

    assert resumed["current_question"]["question_id"] == question_id
    assert resumed["current_grade"]["score"] == 4
    assert resumed["current_grade"]["verdict"] == "Good answer."


async def test_resume_has_no_grade_before_the_question_is_answered(
    api: AsyncClient, llm: EchoClient
) -> None:
    llm.queue(question_reply("first"), grade_reply(), question_reply("second"))
    session_id = await start_session(api)
    question_id = (await api.post(f"/sessions/{session_id}/questions")).json()["question_id"]
    await api.post(
        f"/sessions/{session_id}/answers",
        json={"question_id": question_id, "answer": "It is a mutex."},
    )
    await api.post(f"/sessions/{session_id}/questions")

    resumed = (await api.get(f"/sessions/{session_id}")).json()

    assert resumed["current_question"]["prompt"] == "second"
    assert resumed["current_grade"] is None


async def test_resume_returns_the_latest_question(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue(question_reply("first"), question_reply("second"))
    session_id = await start_session(api)
    await api.post(f"/sessions/{session_id}/questions")
    await api.post(f"/sessions/{session_id}/questions")

    resumed = await api.get(f"/sessions/{session_id}")

    assert resumed.json()["current_question"]["prompt"] == "second"


async def test_resume_before_any_question_has_no_current_question(api: AsyncClient) -> None:
    session_id = await start_session(api)

    resumed = await api.get(f"/sessions/{session_id}")

    assert resumed.status_code == 200
    assert resumed.json()["current_question"] is None


async def test_resume_never_leaks_the_key_points(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue(question_reply(key_points=["secret point"]))
    session_id = await start_session(api)
    await api.post(f"/sessions/{session_id}/questions")

    resumed = await api.get(f"/sessions/{session_id}")

    assert "secret point" not in resumed.text
    assert "key_points" not in resumed.text


async def test_resuming_an_unknown_session_is_not_found(api: AsyncClient) -> None:
    response = await api.get("/sessions/nope")

    assert response.status_code == 404


async def test_a_resumed_question_can_still_be_answered(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue(question_reply(), grade_reply(score=5))
    session_id = await start_session(api)
    await api.post(f"/sessions/{session_id}/questions")
    resumed = (await api.get(f"/sessions/{session_id}")).json()

    graded = await api.post(
        f"/sessions/{session_id}/answers",
        json={
            "question_id": resumed["current_question"]["question_id"],
            "answer": "It is a mutex.",
        },
    )

    assert graded.status_code == 200
    assert graded.json()["score"] == 5


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


async def answer_a_question(api: AsyncClient, session_id: str) -> str:
    """Ask and answer one question, returning its id."""
    question_id = (await api.post(f"/sessions/{session_id}/questions")).json()["question_id"]
    await api.post(
        f"/sessions/{session_id}/answers",
        json={"question_id": question_id, "answer": "It is a mutex."},
    )
    return question_id


async def test_explanation_is_available_once_the_question_is_answered(
    api: AsyncClient, llm: EchoClient
) -> None:
    llm.queue(question_reply(), grade_reply(), explanation_reply("The GIL is a mutex."))
    session_id = await start_session(api)
    question_id = await answer_a_question(api, session_id)

    response = await api.post(f"/sessions/{session_id}/questions/{question_id}/explanation")

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "The GIL is a mutex."
    assert body["points"][0]["point"] == "a mutex"
    assert body["pitfalls"]


async def test_explanation_is_generated_once_and_reused(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue(question_reply(), grade_reply(), explanation_reply("Generated once."))
    session_id = await start_session(api)
    question_id = await answer_a_question(api, session_id)
    calls_before = len(llm.calls)

    first = await api.post(f"/sessions/{session_id}/questions/{question_id}/explanation")
    second = await api.post(f"/sessions/{session_id}/questions/{question_id}/explanation")

    assert first.json() == second.json() == {**first.json(), "answer": "Generated once."}
    assert len(llm.calls) == calls_before + 1


async def test_explanation_before_answering_is_refused(api: AsyncClient, llm: EchoClient) -> None:
    llm.queue(question_reply(key_points=["secret point"]))
    session_id = await start_session(api)
    question_id = (await api.post(f"/sessions/{session_id}/questions")).json()["question_id"]

    response = await api.post(f"/sessions/{session_id}/questions/{question_id}/explanation")

    assert response.status_code == 409
    assert "secret point" not in response.text


async def test_explaining_an_unknown_question_is_not_found(api: AsyncClient) -> None:
    session_id = await start_session(api)

    response = await api.post(f"/sessions/{session_id}/questions/nope/explanation")

    assert response.status_code == 404


async def test_explaining_in_an_unknown_session_is_not_found(api: AsyncClient) -> None:
    response = await api.post("/sessions/nope/questions/nope/explanation")

    assert response.status_code == 404


async def test_resume_returns_the_explanation_already_read(
    api: AsyncClient, llm: EchoClient
) -> None:
    llm.queue(question_reply(), grade_reply(), explanation_reply("Already read."))
    session_id = await start_session(api)
    question_id = await answer_a_question(api, session_id)
    await api.post(f"/sessions/{session_id}/questions/{question_id}/explanation")

    resumed = (await api.get(f"/sessions/{session_id}")).json()

    assert resumed["current_explanation"]["answer"] == "Already read."


async def test_resume_has_no_explanation_before_learn_more(
    api: AsyncClient, llm: EchoClient
) -> None:
    llm.queue(question_reply(), grade_reply())
    session_id = await start_session(api)
    await answer_a_question(api, session_id)

    resumed = (await api.get(f"/sessions/{session_id}")).json()

    assert resumed["current_explanation"] is None
