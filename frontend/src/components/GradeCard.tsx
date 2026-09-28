import { useState } from "react";

import { MAX_SCORE } from "../api/types";
import type { Explanation, Grade } from "../api/types";
import { ExplanationPanel } from "./ExplanationPanel";

type Props = {
  grade: Grade;
  explanation: Explanation | null;
  disabled: boolean;
  onLearnMore: () => void;
  onNext: () => void;
};

export function GradeCard({ grade, explanation, disabled, onLearnMore, onNext }: Props) {
  const [shown, setShown] = useState(false);

  // The first click has to fetch the worked answer; once it is in hand the
  // button only folds it away and back, without asking the model again.
  function toggle() {
    if (explanation === null) {
      setShown(true);
      onLearnMore();
      return;
    }
    setShown((was) => !was);
  }

  return (
    <section className="card">
      <p className="score" data-testid="score">
        {grade.score} / {MAX_SCORE}
      </p>
      <p>{grade.verdict}</p>

      <PointList title="Covered" points={grade.covered} className="covered" />
      <PointList title="Missed" points={grade.missed} className="missed" />

      {shown && explanation !== null && <ExplanationPanel explanation={explanation} />}

      <div className="actions">
        <button type="button" className="secondary" onClick={toggle} disabled={disabled}>
          {shown && explanation !== null ? "Hide details" : "Learn more"}
        </button>
        <button type="button" onClick={onNext} disabled={disabled}>
          Next question
        </button>
      </div>
    </section>
  );
}

function PointList({
  title,
  points,
  className,
}: {
  title: string;
  points: string[];
  className: string;
}) {
  if (points.length === 0) return null;
  return (
    <div className={className}>
      <h3>{title}</h3>
      <ul>
        {points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
    </div>
  );
}
