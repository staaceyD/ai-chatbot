# ai-chatbot

A local chatbot for practising software engineering interview questions
(Python, React, JavaScript). Answers are graded by a model running on your
own machine.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Ollama](https://ollama.com/download)

## Setup

Install the backend dependencies:

```sh
cd backend
uv sync --all-groups
```

Start Ollama and pull a model:

```sh
ollama serve
ollama pull llama3.1:8b
```

## Run

```sh
cd backend
uv run uvicorn interview_bot.main:app --reload
```

The API is on http://localhost:8000, interactive docs on
http://localhost:8000/docs.

Check it came up:

```sh
curl http://localhost:8000/health
```

## Configuration

Settings are read from the environment, or from `backend/.env`. All of them
have defaults, so you only need to set what you want to change.

| Variable | Default | Description |
| --- | --- | --- |
| `INTERVIEW_BOT_LLM_BACKEND` | `ollama` | Model provider: `ollama`, or `echo` for canned replies |
| `INTERVIEW_BOT_OLLAMA_MODEL` | `llama3.1:8b` | Which Ollama model to use |
| `INTERVIEW_BOT_OLLAMA_BASE_URL` | `http://localhost:11434` | Where Ollama is listening |
| `INTERVIEW_BOT_LLM_TIMEOUT_SECONDS` | `120` | Give up on a slow model after this long |
| `INTERVIEW_BOT_CORS_ORIGINS` | `["http://localhost:5173"]` | Origins allowed to call the API |

To run without Ollama at all:

```sh
INTERVIEW_BOT_LLM_BACKEND=echo uv run uvicorn interview_bot.main:app --reload
```

## Tests

```sh
cd backend
uv run pytest
uv run ruff check .
uv run ruff format .
```
