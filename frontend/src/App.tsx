import { useState } from "react";

import { api as defaultApi, ApiError } from "./api/client";
import type { Api } from "./api/client";
import type { Difficulty, Grade, Question, Topic } from "./api/types";
import { GradeCard } from "./components/GradeCard";
import { QuestionCard } from "./components/QuestionCard";
import { TopicPicker } from "./components/TopicPicker";

export function App({ api = defaultApi }: { api?: Api }) {
  const [topic, setTopic] = useState<Topic>("python");
  const [difficulty, setDifficulty] = useState<Difficulty>("mid");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [grade, setGrade] = useState<Grade | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  // Each step commits its state only once every request has resolved, so the
  // screen never blanks out while the model is thinking.
  const start = () =>
    run(async () => {
      const session = await api.startSession(topic, difficulty);
      const first = await api.nextQuestion(session.session_id);
      setSessionId(session.session_id);
      setQuestion(first);
      setGrade(null);
    });

  const next = () =>
    run(async () => {
      if (!sessionId) return;
      const following = await api.nextQuestion(sessionId);
      setQuestion(following);
      setGrade(null);
    });

  const answer = (text: string) =>
    run(async () => {
      if (!sessionId || !question) return;
      setGrade(await api.submitAnswer(sessionId, question.question_id, text));
    });

  return (
    <main>
      <h1>Interview Bot</h1>

      {sessionId === null ? (
        <TopicPicker
          topic={topic}
          difficulty={difficulty}
          disabled={busy}
          onTopicChange={setTopic}
          onDifficultyChange={setDifficulty}
          onStart={start}
        />
      ) : (
        <>
          {question && !grade && (
            <QuestionCard
              // Remount on a new question so the textarea starts empty.
              key={question.question_id}
              question={question}
              disabled={busy}
              onSubmit={answer}
            />
          )}
          {grade && <GradeCard grade={grade} disabled={busy} onNext={next} />}
        </>
      )}

      {busy && <p role="status">Thinking…</p>}
      {error && <p role="alert">{error}</p>}
    </main>
  );
}
