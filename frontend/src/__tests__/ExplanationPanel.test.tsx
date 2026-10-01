import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExplanationPanel } from "../components/ExplanationPanel";
import type { Explanation } from "../api/types";

function anExplanation(overrides: Partial<Explanation> = {}): Explanation {
  return { answer: "The GIL is one mutex.", points: [], pitfalls: [], ...overrides };
}

describe("the worked answer", () => {
  it("splits the prose into paragraphs on blank lines", () => {
    render(
      <ExplanationPanel
        explanation={anExplanation({ answer: "First paragraph.\n\nSecond paragraph." })}
      />,
    );

    expect(screen.getByText("First paragraph.")).toBeInTheDocument();
    expect(screen.getByText("Second paragraph.")).toBeInTheDocument();
  });

  it("renders a fenced example as code, keeping its line breaks", () => {
    const answer = "Like this:\n\n```python\ndef f():\n    return 1\n```\n\nAnd that is all.";

    render(<ExplanationPanel explanation={anExplanation({ answer })} />);

    const code = screen.getByText(/def f\(\):/);
    expect(code.tagName).toBe("CODE");
    expect(code.closest("pre")).not.toBeNull();
    expect(code.textContent).toBe("def f():\n    return 1");
    expect(screen.getByText("And that is all.")).toBeInTheDocument();
  });

  it("keeps a tag it does not recognise out of the code", () => {
    const answer = "```c++\nint x = 1;\n```";

    render(<ExplanationPanel explanation={anExplanation({ answer })} />);

    const code = screen.getByText(/int x = 1;/);
    expect(code.tagName).toBe("CODE");
    expect(code.textContent).toBe("int x = 1;");
  });

  it("keeps the first line of a fence the model opened without a newline", () => {
    // A tag is only a tag on its own line, so `def` here is code, not a label.
    const answer = "```def f():\n    return 1\n```";

    render(<ExplanationPanel explanation={anExplanation({ answer })} />);

    expect(screen.getByText(/def f\(\):/)).toBeInTheDocument();
  });

  it("renders every key point even when the model repeats one", () => {
    // Model output is not unique enough to key a list by, and a duplicate key
    // costs one of the entries on the next render.
    const complained = vi.spyOn(console, "error").mockImplementation(() => {});
    const { rerender } = render(
      <ExplanationPanel
        explanation={anExplanation({
          points: [
            { point: "a mutex", detail: "It guards interpreter state." },
            { point: "a mutex", detail: "Only one thread runs bytecode." },
          ],
          pitfalls: ["Threads on CPU-bound work", "Threads on CPU-bound work"],
        })}
      />,
    );
    rerender(
      <ExplanationPanel
        explanation={anExplanation({
          points: [
            { point: "a mutex", detail: "It guards interpreter state." },
            { point: "a mutex", detail: "Only one thread runs bytecode." },
          ],
          pitfalls: ["Threads on CPU-bound work", "Threads on CPU-bound work"],
        })}
      />,
    );

    expect(screen.getAllByText("a mutex")).toHaveLength(2);
    expect(screen.getAllByText("Threads on CPU-bound work")).toHaveLength(2);
    expect(complained).not.toHaveBeenCalled();
    complained.mockRestore();
  });

  it("renders backticked identifiers as code rather than showing the backticks", () => {
    render(
      <ExplanationPanel
        explanation={anExplanation({ answer: "Call `__getattr__` when it is missing." })}
      />,
    );

    expect(screen.getByText("__getattr__").tagName).toBe("CODE");
    expect(screen.queryByText(/`/)).not.toBeInTheDocument();
  });

  it("expands each key point and lists the pitfalls", () => {
    render(
      <ExplanationPanel
        explanation={anExplanation({
          points: [{ point: "a mutex", detail: "It guards interpreter state." }],
          pitfalls: ["Reaching for threads on CPU-bound work"],
        })}
      />,
    );

    expect(screen.getByText("a mutex")).toBeInTheDocument();
    expect(screen.getByText("It guards interpreter state.")).toBeInTheDocument();
    expect(screen.getByText("Reaching for threads on CPU-bound work")).toBeInTheDocument();
  });

  it("leaves out the sections a weaker model skipped", () => {
    render(<ExplanationPanel explanation={anExplanation()} />);

    expect(screen.getByText("The GIL is one mutex.")).toBeInTheDocument();
    expect(screen.queryByText(/point by point/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/common pitfalls/i)).not.toBeInTheDocument();
  });
});
