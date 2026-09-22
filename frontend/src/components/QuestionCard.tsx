import { useState } from "react";

import type { Question } from "../api/types";

type Props = {
  question: Question;
  disabled: boolean;
  onSubmit: (answer: string) => void;
};

export function QuestionCard({ question, disabled, onSubmit }: Props) {
  const [answer, setAnswer] = useState("");

  return (
    <section className="card">
      <p className="tag">
        {question.topic} · {question.difficulty}
      </p>
      <h2>{question.prompt}</h2>

      <label htmlFor="answer">Your answer</label>
      <textarea
        id="answer"
        rows={8}
        value={answer}
        disabled={disabled}
        placeholder="Answer in a few sentences, as you would out loud."
        onChange={(event) => setAnswer(event.target.value)}
      />

      <button
        type="button"
        onClick={() => onSubmit(answer)}
        disabled={disabled || answer.trim() === ""}
      >
        Submit answer
      </button>
    </section>
  );
}
