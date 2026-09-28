import json
from pathlib import Path

import aiosqlite

from interview_bot.domain import Difficulty, Explanation, Grade, Question, Topic
from interview_bot.store.base import Session, new_session_id

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    topic      TEXT NOT NULL,
    difficulty TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    id         TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    topic      TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    prompt     TEXT NOT NULL,
    key_points TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS questions_by_session ON questions(session_id, seq);

CREATE TABLE IF NOT EXISTS grades (
    question_id TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    payload     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS grades_by_session ON grades(session_id);

CREATE TABLE IF NOT EXISTS explanations (
    question_id TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    payload     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS explanations_by_session ON explanations(session_id);
"""


class SQLiteSessionStore:
    """Keeps sessions in a SQLite file so they outlive the process."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        if self._path.parent != Path():
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        await self._db.execute("PRAGMA foreign_keys = ON")
        # WAL lets the API keep reading while a question is being written.
        await self._db.execute("PRAGMA journal_mode = WAL")
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def create(self, *, topic: Topic, difficulty: Difficulty) -> Session:
        session = Session(id=new_session_id(), topic=topic, difficulty=difficulty)
        await self._connection().execute(
            "INSERT INTO sessions (id, topic, difficulty) VALUES (?, ?, ?)",
            (session.id, session.topic.value, session.difficulty.value),
        )
        await self._connection().commit()
        return session

    async def get(self, session_id: str) -> Session | None:
        db = self._connection()
        async with db.execute(
            "SELECT topic, difficulty FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None

        session = Session(id=session_id, topic=Topic(row[0]), difficulty=Difficulty(row[1]))
        async with db.execute(
            "SELECT id, topic, difficulty, prompt, key_points"
            " FROM questions WHERE session_id = ? ORDER BY seq",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        session.questions = {row[0]: _to_question(row) for row in rows}

        async with db.execute(
            "SELECT question_id, payload FROM grades WHERE session_id = ?", (session_id,)
        ) as cursor:
            rows = await cursor.fetchall()

        session.grades = {row[0]: Grade.model_validate_json(row[1]) for row in rows}

        async with db.execute(
            "SELECT question_id, payload FROM explanations WHERE session_id = ?", (session_id,)
        ) as cursor:
            rows = await cursor.fetchall()

        session.explanations = {row[0]: Explanation.model_validate_json(row[1]) for row in rows}
        return session

    async def add_question(self, session_id: str, question: Question) -> None:
        await self._connection().execute(
            "INSERT INTO questions (id, session_id, topic, difficulty, prompt, key_points)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                question.id,
                session_id,
                question.topic.value,
                question.difficulty.value,
                question.prompt,
                json.dumps(question.key_points),
            ),
        )
        await self._connection().commit()

    async def record_grade(self, session_id: str, question_id: str, grade: Grade) -> None:
        # Re-answering a question replaces its grade rather than piling up rows.
        await self._connection().execute(
            "INSERT INTO grades (question_id, session_id, payload) VALUES (?, ?, ?)"
            " ON CONFLICT(question_id) DO UPDATE SET payload = excluded.payload",
            (question_id, session_id, grade.model_dump_json()),
        )
        await self._connection().commit()

    async def record_explanation(
        self, session_id: str, question_id: str, explanation: Explanation
    ) -> None:
        # Written once and read back on every "Learn more", so generating it again
        # never costs the reader another wait on the model.
        await self._connection().execute(
            "INSERT INTO explanations (question_id, session_id, payload) VALUES (?, ?, ?)"
            " ON CONFLICT(question_id) DO UPDATE SET payload = excluded.payload",
            (question_id, session_id, explanation.model_dump_json()),
        )
        await self._connection().commit()

    async def aclose(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    def _connection(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Store used before initialize()")
        return self._db


def _to_question(row: aiosqlite.Row) -> Question:
    question_id, topic, difficulty, prompt, key_points = row
    return Question(
        id=question_id,
        topic=Topic(topic),
        difficulty=Difficulty(difficulty),
        prompt=prompt,
        key_points=json.loads(key_points),
    )
