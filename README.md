# ai-chatbot

A local chatbot for practising software engineering interview questions
(Python, React, JavaScript). Answers are graded by a model running on your
own machine.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Ollama](https://ollama.com/download)
- Node 20 or newer, with npm 11 or newer

## Setup

Install the backend dependencies:

```sh
cd backend
uv sync --all-groups
```

Install the frontend dependencies:

```sh
cd frontend
npm install
```

Start Ollama and pull a model:

```sh
ollama serve
ollama pull qwen3:4b-instruct
```

## Run

The app needs both halves running, in two terminals.

Backend:

```sh
cd backend
uv run uvicorn interview_bot.main:app --reload
```

Frontend:

```sh
cd frontend
npm run dev
```

Open http://localhost:5173 and pick a topic. The API is on
http://localhost:8000, with interactive docs on http://localhost:8000/docs.

A grade comes with a **Learn more** button. It writes the answer out in full —
a few paragraphs, every key point expanded, and the mistakes people usually
make — so you can learn the question without going off to search for it. It
only appears once you have answered, and it folds away again with **Hide
details**.

The worked answer is written in the background while you are reading the
question and typing, so by the time you click there is usually nothing left to
wait for.

Refreshing the page picks the interview back up where you left it. Use
**Start over** to drop it and choose a different topic.

Answers are graded by a model running on your machine, so expect each
question and each grade to take a few seconds, and a worked answer to take
longer — it is several times as much writing.

Check the backend came up:

```sh
curl http://localhost:8000/health
```

## Using the API directly

Start a session, ask for a question, then answer it:

```sh
SESSION=$(curl -s -X POST http://localhost:8000/sessions \
  -H 'content-type: application/json' \
  -d '{"topic":"python","difficulty":"mid"}' | jq -r .session_id)

curl -s -X POST http://localhost:8000/sessions/$SESSION/questions | jq

curl -s -X POST http://localhost:8000/sessions/$SESSION/answers \
  -H 'content-type: application/json' \
  -d '{"question_id":"<id from above>","answer":"..."}' | jq
```

Then read the worked answer for that question:

```sh
curl -s -X POST \
  http://localhost:8000/sessions/$SESSION/questions/<question id>/explanation | jq
```

Topics are `python`, `react` and `javascript`; difficulties are `junior`,
`mid` and `senior`.

Sessions are stored in a SQLite file (`backend/interview_bot.db` by default)
and survive a restart, so an interview keeps going across a backend reload.
Delete the file to start clean.

`GET /sessions/{id}` returns a session with the question you were last asked,
the grade for it if you already answered, and the worked answer if you already
read one. That is how the browser resumes after a refresh without re-asking a
question you have finished or regenerating an explanation you have seen.

An explanation is written once and then stored with its question, so asking
again is free. It is refused with a `409` until the question has been answered,
which keeps the endpoint from becoming a way to read the answer instead of
attempting it — including when it was already written ahead.

### Writing answers ahead

A worked answer is the longest thing the model writes, so it starts as soon as
a question is asked rather than when you click **Learn more**. The minutes you
spend reading and typing are minutes the model has nothing else to do.

Ollama serves one request at a time, though, so writing ahead would otherwise
push your grade into a queue behind it. Every prefetch is therefore dropped the
moment a question or a grade needs the model, and started again once that is
done. Answering quickly costs you the head start, never a slower grade.

Set `INTERVIEW_BOT_PREFETCH_EXPLANATIONS=false` to turn it off and write the
answer only when it is asked for.

## Configuration

Settings are read from the environment, or from `backend/.env`. All of them
have defaults, so you only need to set what you want to change.

| Variable | Default | Description |
| --- | --- | --- |
| `INTERVIEW_BOT_LLM_BACKEND` | `ollama` | Model provider: `ollama`, or `echo` for canned replies |
| `INTERVIEW_BOT_OLLAMA_MODEL` | `qwen3:4b-instruct` | Which Ollama model to use |
| `INTERVIEW_BOT_OLLAMA_BASE_URL` | `http://localhost:11434` | Where Ollama is listening |
| `INTERVIEW_BOT_LLM_TIMEOUT_SECONDS` | `300` | Give up on a slow model after this long |
| `INTERVIEW_BOT_PREFETCH_EXPLANATIONS` | `true` | Write worked answers ahead, during the idle time while you answer |
| `INTERVIEW_BOT_STORE_BACKEND` | `sqlite` | Where sessions live: `sqlite`, or `memory` to drop them on exit |
| `INTERVIEW_BOT_SQLITE_PATH` | `interview_bot.db` | SQLite file, relative to where the backend runs |
| `INTERVIEW_BOT_CORS_ORIGINS` | `["http://localhost:5173"]` | Origins allowed to call the API |

The frontend reads `VITE_API_URL` (default `http://localhost:8000`) to find
the backend.

To run without Ollama at all:

```sh
INTERVIEW_BOT_LLM_BACKEND=echo uv run uvicorn interview_bot.main:app --reload
```

## Tests

Backend:

```sh
cd backend
uv run pytest
uv run ruff check .
uv run ruff format .
```

Frontend:

```sh
cd frontend
npm test
npm run lint
npm run typecheck
```

Both suites run on every pull request via GitHub Actions.
