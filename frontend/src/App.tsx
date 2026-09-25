import { useEffect, useRef, useState } from "react";

import { api as defaultApi, ApiError } from "./api/client";
import type { Api } from "./api/client";
import type { Difficulty, Grade, Question, Topic } from "./api/types";
import { GradeCard } from "./components/GradeCard";
import { QuestionCard } from "./components/QuestionCard";
import { TopicPicker } from "./components/TopicPicker";
import { forgetSession, recallSession, rememberSession } from "./storage";

export function App({ api = defaultApi }: { api?: Api }) {
  const [topic, setTopic] = useState<Topic>("python");
  const [difficulty, setDifficulty] = useState<Difficulty>("mid");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [grade, setGrade] = useState<Grade | null>(null);
  const [busy, setBusy] = useState(false);
  const [resuming, setResuming] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const resumed = useRef(false);

  useEffect(() => {
    if (resumed.current) return;
    resumed.current = true;

    const stored = recallSession();
    if (stored === null) {
      setResuming(false);
      return;
    }

    void (async () => {
      try {
        const state = await api.resumeSession(stored);
        // A session with no question yet has nothing to return to.
        if (state.current_question === null) {
          forgetSession();
          return;
        }
        setSessionId(state.session_id);
        setTopic(state.topic);
        setDifficulty(state.difficulty);
        setQuestion(state.current_question);
      } catch (caught) {
        forgetSession();
        if (!(caught instanceof ApiError) || caught.status !== 404) {
          setError("Could not restore your last interview, so this is a fresh start.");
        }
      } finally {
        setResuming(false);
      }
    })();
  }, [api]);

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
      rememberSession(session.session_id);
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

  function startOver() {
    forgetSession();
    setSessionId(null);
    setQuestion(null);
    setGrade(null);
    setError(null);
  }

  if (resuming) {
    return (
      <main>
        <h1>Interview Bot</h1>
        <p role="status">Restoring your interview…</p>
      </main>
    );
  }

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

          <button type="button" className="secondary" onClick={startOver} disabled={busy}>
            Start over
          </button>
        </>
      )}

      {busy && <p role="status">Thinking…</p>}
      {error && <p role="alert">{error}</p>}
    </main>
  );
}
