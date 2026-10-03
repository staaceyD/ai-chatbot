import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TOPIC_GROUPS } from "../api/types";
import type { Topic } from "../api/types";
import { TopicPicker } from "../components/TopicPicker";

function renderPicker(topics: Topic[] = ["python"], onTopicsChange = vi.fn()) {
  render(
    <TopicPicker
      topics={topics}
      difficulty="mid"
      disabled={false}
      onTopicsChange={onTopicsChange}
      onDifficultyChange={vi.fn()}
      onStart={vi.fn()}
    />,
  );
  return onTopicsChange;
}

describe("the topic picker", () => {
  it("offers every topic under its group heading", () => {
    renderPicker();

    for (const group of TOPIC_GROUPS) {
      const heading = screen.getByRole("group", { name: group.label });
      for (const topic of group.topics) {
        expect(screen.getByRole("checkbox", { name: topic.label })).toBe(
          heading.querySelector(`input[value="${topic.value}"]`),
        );
      }
    }
  });

  it("shows which topics are already chosen", () => {
    renderPicker(["python", "databases"]);

    expect(screen.getByRole("checkbox", { name: "Python" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Databases and SQL" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "React" })).not.toBeChecked();
  });

  it("adds a topic to the ones already chosen rather than replacing them", async () => {
    const onTopicsChange = renderPicker(["python"]);
    const user = userEvent.setup();

    await user.click(screen.getByRole("checkbox", { name: "Data structures" }));

    expect(onTopicsChange).toHaveBeenCalledWith(["python", "data_structures"]);
  });

  it("reports the chosen topics by value, in the order they are listed", async () => {
    // Clicked out of order: a session should still read back in picker order.
    const onTopicsChange = renderPicker(["security"]);
    const user = userEvent.setup();

    await user.click(screen.getByRole("checkbox", { name: "React" }));

    expect(onTopicsChange).toHaveBeenCalledWith(["react", "security"]);
  });

  it("drops a topic that is unticked", async () => {
    const onTopicsChange = renderPicker(["python", "react"]);
    const user = userEvent.setup();

    await user.click(screen.getByRole("checkbox", { name: "Python" }));

    expect(onTopicsChange).toHaveBeenCalledWith(["react"]);
  });

  it("cannot start an interview with no topic at all", () => {
    renderPicker([]);

    expect(screen.getByRole("button", { name: /start interview/i })).toBeDisabled();
    expect(screen.getByText(/at least one topic/i)).toBeInTheDocument();
  });

  it("can start an interview as soon as one topic is ticked", () => {
    renderPicker(["python"]);

    expect(screen.getByRole("button", { name: /start interview/i })).toBeEnabled();
  });
});
