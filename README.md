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

Answers are graded by a model running on your machine, so expect each
question and each grade to take a few seconds.

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

Topics are `python`, `react` and `javascript`; difficulties are `junior`,
`mid` and `senior`. Sessions live in memory and are lost on restart.

## Configuration

Settings are read from the environment, or from `backend/.env`. All of them
have defaults, so you only need to set what you want to change.

| Variable | Default | Description |
| --- | --- | --- |
| `INTERVIEW_BOT_LLM_BACKEND` | `ollama` | Model provider: `ollama`, or `echo` for canned replies |
| `INTERVIEW_BOT_OLLAMA_MODEL` | `qwen3:4b-instruct` | Which Ollama model to use |
| `INTERVIEW_BOT_OLLAMA_BASE_URL` | `http://localhost:11434` | Where Ollama is listening |
| `INTERVIEW_BOT_LLM_TIMEOUT_SECONDS` | `120` | Give up on a slow model after this long |
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
