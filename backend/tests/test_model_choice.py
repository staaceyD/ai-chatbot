"""Choosing the model per interview, and switching it part way through."""

from httpx import AsyncClient

from interview_bot.llm.echo import EchoClient
from replies import grade_reply, question_reply


async def test_a_session_runs_on_the_configured_provider_by_default(api: AsyncClient) -> None:
    response = await api.post("/sessions", json={"topic": "python"})

    assert response.json()["model_provider"] == "echo"


async def test_a_session_can_choose_its_model(api: AsyncClient) -> None:
    response = await api.post("/sessions", json={"topic": "python", "model_provider": "anthropic"})

    assert response.status_code == 201
    assert response.json()["model_provider"] == "anthropic"


async def test_an_unknown_model_is_refused(api: AsyncClient) -> None:
    response = await api.post("/sessions", json={"topic": "python", "model_provider": "gpt"})

    assert response.status_code == 422


async def test_switching_model_changes_the_session(api: AsyncClient) -> None:
    session_id = (await api.post("/sessions", json={"topic": "python"})).json()["session_id"]

    switched = await api.patch(f"/sessions/{session_id}", json={"model_provider": "ollama"})

    assert switched.status_code == 200
    assert switched.json()["model_provider"] == "ollama"
    assert (await api.get(f"/sessions/{session_id}")).json()["model_provider"] == "ollama"


async def test_switching_to_the_model_already_in_use_is_a_no_op(api: AsyncClient) -> None:
    session_id = (await api.post("/sessions", json={"topic": "python"})).json()["session_id"]

    switched = await api.patch(f"/sessions/{session_id}", json={"model_provider": "echo"})

    assert switched.status_code == 200
    assert switched.json()["model_provider"] == "echo"


async def test_switching_an_unknown_session_is_not_found(api: AsyncClient) -> None:
    response = await api.patch("/sessions/nope", json={"model_provider": "ollama"})

    assert response.status_code == 404


async def test_switching_to_an_unknown_model_is_refused(api: AsyncClient) -> None:
    session_id = (await api.post("/sessions", json={"topic": "python"})).json()["session_id"]

    response = await api.patch(f"/sessions/{session_id}", json={"model_provider": "gpt"})

    assert response.status_code == 422
    assert (await api.get(f"/sessions/{session_id}")).json()["model_provider"] == "echo"


async def test_a_resumed_session_keeps_the_model_it_was_started_on(
    api: AsyncClient, llm: EchoClient
) -> None:
    llm.queue(question_reply("What is the GIL?"))
    session_id = (
        await api.post("/sessions", json={"topic": "python", "model_provider": "anthropic"})
    ).json()["session_id"]
    await api.post(f"/sessions/{session_id}/questions")

    resumed = await api.get(f"/sessions/{session_id}")

    assert resumed.json()["model_provider"] == "anthropic"


async def test_the_whole_round_runs_on_the_chosen_model(api: AsyncClient, llm: EchoClient) -> None:
    """Every call of an interview goes to the model the session chose."""
    llm.queue(question_reply("What is the GIL?"), grade_reply(score=4))
    session_id = (
        await api.post("/sessions", json={"topic": "python", "model_provider": "ollama"})
    ).json()["session_id"]

    question = (await api.post(f"/sessions/{session_id}/questions")).json()
    graded = await api.post(
        f"/sessions/{session_id}/answers",
        json={"question_id": question["question_id"], "answer": "It is a mutex."},
    )

    assert graded.status_code == 200
    # The injected client stands in for every provider, so reaching it at all
    # proves the session's own choice was the one looked up.
    assert len(llm.calls) == 2
