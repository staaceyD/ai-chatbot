import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TOPIC_GROUPS } from "../api/types";
import { TopicPicker } from "../components/TopicPicker";

function renderPicker(onTopicChange = vi.fn()) {
  render(
    <TopicPicker
      topic="python"
      difficulty="mid"
      disabled={false}
      onTopicChange={onTopicChange}
      onDifficultyChange={vi.fn()}
      onStart={vi.fn()}
    />,
  );
  return onTopicChange;
}

describe("the topic picker", () => {
  it("offers every topic under its group heading", () => {
    renderPicker();

    for (const group of TOPIC_GROUPS) {
      const heading = screen.getByRole("group", { name: group.label });
      for (const topic of group.topics) {
        expect(screen.getByRole("option", { name: topic.label })).toBe(
          heading.querySelector(`option[value="${topic.value}"]`),
        );
      }
    }
  });

  it("reports the chosen topic by its value, not its label", async () => {
    const onTopicChange = renderPicker();
    const user = userEvent.setup();

    await user.selectOptions(screen.getByLabelText(/topic/i), "Data structures");

    expect(onTopicChange).toHaveBeenCalledWith("data_structures");
  });
});
