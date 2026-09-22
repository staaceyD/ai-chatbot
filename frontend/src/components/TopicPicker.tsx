import { DIFFICULTIES, TOPICS } from "../api/types";
import type { Difficulty, Topic } from "../api/types";

type Props = {
  topic: Topic;
  difficulty: Difficulty;
  disabled: boolean;
  onTopicChange: (topic: Topic) => void;
  onDifficultyChange: (difficulty: Difficulty) => void;
  onStart: () => void;
};

export function TopicPicker({
  topic,
  difficulty,
  disabled,
  onTopicChange,
  onDifficultyChange,
  onStart,
}: Props) {
  return (
    <section className="card">
      <h2>Pick a topic</h2>

      <label htmlFor="topic">Topic</label>
      <select
        id="topic"
        value={topic}
        disabled={disabled}
        onChange={(event) => onTopicChange(event.target.value as Topic)}
      >
        {TOPICS.map((value) => (
          <option key={value} value={value}>
            {value}
          </option>
        ))}
      </select>

      <label htmlFor="difficulty">Difficulty</label>
      <select
        id="difficulty"
        value={difficulty}
        disabled={disabled}
        onChange={(event) => onDifficultyChange(event.target.value as Difficulty)}
      >
        {DIFFICULTIES.map((value) => (
          <option key={value} value={value}>
            {value}
          </option>
        ))}
      </select>

      <button type="button" onClick={onStart} disabled={disabled}>
        Start interview
      </button>
    </section>
  );
}
