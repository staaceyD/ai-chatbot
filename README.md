# ai-chatbot

A local chatbot for practising software engineering interview questions —
languages and frameworks as well as engineering fundamentals such as system
design, databases, algorithms and data structures. Tick several topics and the
questions jump between them, shuffled, the way a real interview does. Answers
are graded by a model — either one running on your own machine, or a hosted Claude model if
you would rather have the speed.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Ollama](https://ollama.com/download), unless you run against a hosted model
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

Or skip Ollama and use a hosted model instead — see [Running against a hosted
model](#running-against-a-hosted-model).

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

Open http://localhost:5173 and tick the topics you want. The API is on
http://localhost:8000, with interactive docs on http://localhost:8000/docs.

Ticking more than one topic makes it a mixed interview: each question comes
from one of them, shuffled, and the tag above the question says which — see
[Mixed topics](#mixed-topics).

A **Model** dropdown above the topics sits over the whole interview. It starts
on **Ollama (free)**, the model on your own machine, and switching it to
**Claude** moves the interview onto the hosted model from the next question
onwards — see [Running against a hosted model](#running-against-a-hosted-model)
for what that needs and what it costs.

A grade comes with a **Learn more** button. It writes the answer out in full —
a few paragraphs, every key point expanded, and the mistakes people usually
make — so you can learn the question without going off to search for it. It
only appears once you have answered, and it folds away again with **Hide
details**.

The worked answer is written in the background while you are reading the
question and typing, so by the time you click there is usually nothing left to
wait for.

Refreshing the page picks the interview back up where you left it. Use
**Start over** to drop it and choose different topics.

On the local model, expect each question and each grade to take a few
seconds, and a worked answer to take longer — it is several times as much
writing. A hosted model is quicker on all three.

Check the backend came up:

```sh
curl http://localhost:8000/health
```

## Using the API directly

Start a session, ask for a question, then answer it:

```sh
SESSION=$(curl -s -X POST http://localhost:8000/sessions \
  -H 'content-type: application/json' \
  -d '{"topics":["python"],"difficulty":"mid"}' | jq -r .session_id)

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

`topics` is a list, and an interview can draw on as many as you like — one is
an interview about that topic, several make a mixed one. Difficulties are
`junior`, `mid` and `senior`. Topics are:

| Languages and frameworks | Engineering fundamentals |
| --- | --- |
| `python` | `system_design`, `databases`, `algorithms` |
| `javascript` | `data_structures`, `concurrency`, `networking` |
| `typescript` | `api_design`, `security`, `testing` |
| `react` | `operating_systems`, `devops` |

```sh
# One mixed interview over three subjects
curl -s -X POST http://localhost:8000/sessions \
  -H 'content-type: application/json' \
  -d '{"topics":["system_design","databases","concurrency"]}' | jq
```

Each topic carries its own scope in `backend/src/interview_bot/prompts.py`
(`TOPIC_SCOPES`), which is what keeps a question about, say, `databases` on
indexes and isolation levels rather than drifting into generic advice. Adding a
topic means adding it to `Topic`, to `TOPIC_LABELS` and `TOPIC_SCOPES`, and to
`TOPIC_GROUPS` in `frontend/src/api/types.ts`.

Sessions are stored in a SQLite file (`backend/interview_bot.db` by default)
and survive a restart, so an interview keeps going across a backend reload.
Delete the file to start clean. A session written by a version before mixed
topics is migrated when the file opens: the interview it was on comes back as
the one topic it covers.

`GET /sessions/{id}` returns a session with the question you were last asked,
the grade for it if you already answered, and the worked answer if you already
read one. That is how the browser resumes after a refresh without re-asking a
question you have finished or regenerating an explanation you have seen.

An explanation is written once and then stored with its question, so asking
again is free. It is refused with a `409` until the question has been answered,
which keeps the endpoint from becoming a way to read the answer instead of
attempting it — including when it was already written ahead. A resume is held
to the same rule: an ungraded question comes back without its worked answer,
even when one is already sitting in the store.

### Mixed topics

Which topic a question comes from is decided when it is asked, in
`backend/src/interview_bot/rotation.py`, from the topics of the questions
already asked. Two rules shape it:

- **Shuffled, not in order.** Working through the list would make the interview
  predictable after the first round.
- **Every topic once before any topic twice.** Shuffling alone would ask four
  Python questions before touching databases. The choice is only among the
  topics asked least so far, so a session is a shuffled round of the chosen
  topics, then another — and the topic that closed one round never opens the
  next, which would read as a repeat.

The question is still generated for one topic at a time, with that topic's
scope: a prompt naming three subjects at once produces a question about none of
them. Previous questions are sent to the model whatever topic they came from, so
a mixed interview does not circle back to the same ground from another angle.

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

Switching model mid-interview drops a worked answer being written ahead: it is
the old model's, nobody has asked for it yet, and the next request writes it
again on the new one. An answer somebody is already waiting on is left to
finish.

## Choosing the model

Which model an interview runs on belongs to the session, not to the process.
It is chosen when the session starts and can be changed at any point:

```sh
# Start an interview on a specific model
curl -s -X POST http://localhost:8000/sessions \
  -H 'content-type: application/json' \
  -d '{"topics":["python"],"difficulty":"mid","model_provider":"anthropic"}' | jq

# Move a running interview onto another one
curl -s -X PATCH http://localhost:8000/sessions/$SESSION \
  -H 'content-type: application/json' \
  -d '{"model_provider":"ollama"}' | jq
```

Providers are `ollama`, `anthropic` and `echo`. A request that leaves
`model_provider` out gets `INTERVIEW_BOT_DEFAULT_MODEL_PROVIDER`; the browser
always sends one, so that setting is the default for API callers rather than
for the dropdown, which starts on Ollama. `GET /health` lists every provider a
session can be switched to.

The choice is stored with the session, so resuming after a refresh comes back
on the model the interview was running on, and every call of that interview —
the question, the grade and the worked answer — goes to it.

## Configuration

Settings are read from the environment, or from `backend/.env`. All of them
have defaults, so you only need to set what you want to change.

| Variable | Default | Description |
| --- | --- | --- |
| `INTERVIEW_BOT_DEFAULT_MODEL_PROVIDER` | `ollama` | Provider a session gets when it does not choose one: `ollama`, `anthropic`, or `echo` for canned replies |
| `INTERVIEW_BOT_OLLAMA_MODEL` | `qwen3:4b-instruct` | Which Ollama model to use |
| `INTERVIEW_BOT_OLLAMA_BASE_URL` | `http://localhost:11434` | Where Ollama is listening |
| `INTERVIEW_BOT_ANTHROPIC_MODEL` | `claude-haiku-4-5` | Which hosted Claude model to use |
| `INTERVIEW_BOT_ANTHROPIC_MAX_TOKENS` | `4096` | Longest reply the hosted model may write |
| `INTERVIEW_BOT_LLM_TIMEOUT_SECONDS` | `120` | Give up on a slow model after this long |
| `INTERVIEW_BOT_LLM_EXPLAIN_TIMEOUT_SECONDS` | `300` | The same, for a worked answer, which is several times longer |
| `INTERVIEW_BOT_PREFETCH_EXPLANATIONS` | `true` | Write worked answers ahead, during the idle time while you answer |
| `INTERVIEW_BOT_STORE_BACKEND` | `sqlite` | Where sessions live: `sqlite`, or `memory` to drop them on exit |
| `INTERVIEW_BOT_SQLITE_PATH` | `interview_bot.db` | SQLite file, relative to where the backend runs |
| `INTERVIEW_BOT_CORS_ORIGINS` | `["http://localhost:5173"]` | Origins allowed to call the API |

The frontend reads `VITE_API_URL` (default `http://localhost:8000`) to find
the backend.

To run without a model at all:

```sh
INTERVIEW_BOT_DEFAULT_MODEL_PROVIDER=echo uv run uvicorn interview_bot.main:app --reload
```

## Running against a hosted model

A 4B model on a laptop is the slow part of this app. Pointing it at a hosted
Claude model instead needs an API key from the
[Claude Console](https://platform.claude.com/settings/keys) and one
environment variable:

```sh
export ANTHROPIC_API_KEY=sk-ant-...
INTERVIEW_BOT_DEFAULT_MODEL_PROVIDER=anthropic uv run uvicorn interview_bot.main:app --reload
```

The default is `claude-haiku-4-5`, the cheapest model Anthropic serves. One
question — asking it, grading the answer, and writing the worked answer — is
about 1,000 tokens in and 1,250 out, so roughly $0.007, or $0.07 for a
ten-question session. Switching to `claude-sonnet-5` is about twice that.

Nothing else changes: the same prompts, the same stored sessions, and the
`echo` provider still works for tests. Set
`INTERVIEW_BOT_DEFAULT_MODEL_PROVIDER` back to `ollama`, or just pick Ollama in
the dropdown, to go back to running locally.

A Claude Pro or Max subscription does not cover this: the API is billed per
token, separately from the subscription, and a subscription cannot be used to
authenticate requests from an app like this one. Running on `ollama` is the
way to spend nothing.

### Capping what it can spend

The app has no budget of its own — the cap belongs on the key, where nothing
in this repo can get around it:

1. In the Console, under
   [Settings > Workspaces](https://platform.claude.com/settings/workspaces),
   create a workspace (the Default Workspace cannot carry limits, and the
   section only appears once the account is set up as an organization).
2. On its **Spend limits** tab, set a monthly ceiling and an alert threshold.
3. Create an API key scoped to that workspace, and use that key here.

Spending by this app then stops at the ceiling whatever the code does.

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
