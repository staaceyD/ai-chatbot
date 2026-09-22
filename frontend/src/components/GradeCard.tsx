import { MAX_SCORE } from "../api/types";
import type { Grade } from "../api/types";

type Props = {
  grade: Grade;
  disabled: boolean;
  onNext: () => void;
};

export function GradeCard({ grade, disabled, onNext }: Props) {
  return (
    <section className="card">
      <p className="score" data-testid="score">
        {grade.score} / {MAX_SCORE}
      </p>
      <p>{grade.verdict}</p>

      <PointList title="Covered" points={grade.covered} className="covered" />
      <PointList title="Missed" points={grade.missed} className="missed" />

      <button type="button" onClick={onNext} disabled={disabled}>
        Next question
      </button>
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
