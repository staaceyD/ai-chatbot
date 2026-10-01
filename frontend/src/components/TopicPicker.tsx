import { DIFFICULTIES, TOPIC_GROUPS } from "../api/types";
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
        {TOPIC_GROUPS.map((group) => (
          <optgroup key={group.label} label={group.label}>
            {group.topics.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </optgroup>
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
