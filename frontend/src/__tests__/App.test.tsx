import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { ApiError } from "../api/client";
import type { Api } from "../api/client";
import type { Grade, Question, Session } from "../api/types";

const session: Session = { session_id: "s1", topic: "python", difficulty: "mid" };

const question: Question = {
  question_id: "q1",
  prompt: "What is the GIL?",
  topic: "python",
  difficulty: "mid",
};

const grade: Grade = {
  score: 4,
  verdict: "Good answer.",
  covered: ["a mutex"],
  missed: ["I/O-bound work"],
};

function fakeApi(overrides: Partial<Api> = {}): Api {
  return {
    startSession: vi.fn().mockResolvedValue(session),
    nextQuestion: vi.fn().mockResolvedValue(question),
    submitAnswer: vi.fn().mockResolvedValue(grade),
    ...overrides,
  };
}

async function startInterview(api: Api) {
  const user = userEvent.setup();
  render(<App api={api} />);
  await user.click(screen.getByRole("button", { name: /start interview/i }));
  await screen.findByText(question.prompt);
  return user;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("starting an interview", () => {
  it("shows the first question for the chosen topic and difficulty", async () => {
    const api = fakeApi();
    const user = userEvent.setup();
    render(<App api={api} />);

    await user.selectOptions(screen.getByLabelText(/topic/i), "react");
    await user.selectOptions(screen.getByLabelText(/difficulty/i), "senior");
    await user.click(screen.getByRole("button", { name: /start interview/i }));

    expect(await screen.findByText(question.prompt)).toBeInTheDocument();
    expect(api.startSession).toHaveBeenCalledWith("react", "senior");
    expect(api.nextQuestion).toHaveBeenCalledWith("s1");
  });
});

describe("while the model is thinking", () => {
  it("keeps the picker on screen until the first question arrives", async () => {
    let release: (question: Question) => void = () => {};
    const api = fakeApi({
      nextQuestion: vi.fn().mockReturnValue(
        new Promise<Question>((resolve) => {
          release = resolve;
        }),
      ),
    });
    const user = userEvent.setup();
    render(<App api={api} />);

    await user.click(screen.getByRole("button", { name: /start interview/i }));

    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start interview/i })).toBeDisabled();

    release(question);
    expect(await screen.findByText(question.prompt)).toBeInTheDocument();
  });

  it("keeps the grade on screen until the next question arrives", async () => {
    let release: (question: Question) => void = () => {};
    const second = { ...question, question_id: "q2", prompt: "What is a decorator?" };
    const api = fakeApi({
      nextQuestion: vi.fn().mockResolvedValueOnce(question).mockReturnValueOnce(
        new Promise<Question>((resolve) => {
          release = resolve;
        }),
      ),
    });
    const user = await startInterview(api);

    await user.type(screen.getByLabelText(/your answer/i), "It is a mutex.");
    await user.click(screen.getByRole("button", { name: /submit answer/i }));
    await screen.findByTestId("score");
    await user.click(screen.getByRole("button", { name: /next question/i }));

    expect(screen.getByTestId("score")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next question/i })).toBeDisabled();

    release(second);
    expect(await screen.findByText(second.prompt)).toBeInTheDocument();
  });
});

describe("answering", () => {
  it("submits the answer and shows the grade", async () => {
    const api = fakeApi();
    const user = await startInterview(api);

    await user.type(screen.getByLabelText(/your answer/i), "It is a mutex.");
    await user.click(screen.getByRole("button", { name: /submit answer/i }));

    expect(await screen.findByTestId("score")).toHaveTextContent("4 / 5");
    expect(screen.getByText("Good answer.")).toBeInTheDocument();
    expect(screen.getByText("a mutex")).toBeInTheDocument();
    expect(screen.getByText("I/O-bound work")).toBeInTheDocument();
    expect(api.submitAnswer).toHaveBeenCalledWith("s1", "q1", "It is a mutex.");
  });

  it("keeps submit disabled until something is typed", async () => {
    const api = fakeApi();
    const user = await startInterview(api);
    const submit = screen.getByRole("button", { name: /submit answer/i });

    expect(submit).toBeDisabled();

    await user.type(screen.getByLabelText(/your answer/i), "   ");
    expect(submit).toBeDisabled();

    await user.type(screen.getByLabelText(/your answer/i), "real answer");
    expect(submit).toBeEnabled();
  });
});

describe("moving on", () => {
  it("clears the previous answer when the next question arrives", async () => {
    const second = { ...question, question_id: "q2", prompt: "What is a decorator?" };
    const api = fakeApi({
      nextQuestion: vi
        .fn()
        .mockResolvedValueOnce(question)
        .mockResolvedValueOnce(second),
    });
    const user = await startInterview(api);

    await user.type(screen.getByLabelText(/your answer/i), "It is a mutex.");
    await user.click(screen.getByRole("button", { name: /submit answer/i }));
    await screen.findByTestId("score");
    await user.click(screen.getByRole("button", { name: /next question/i }));

    expect(await screen.findByText(second.prompt)).toBeInTheDocument();
    expect(screen.getByLabelText(/your answer/i)).toHaveValue("");
    expect(screen.queryByTestId("score")).not.toBeInTheDocument();
  });
});

describe("errors", () => {
  it("shows the backend message when the model is unavailable", async () => {
    const api = fakeApi({
      nextQuestion: vi
        .fn()
        .mockRejectedValue(new ApiError("The model is unavailable: boom")),
    });
    const user = userEvent.setup();
    render(<App api={api} />);

    await user.click(screen.getByRole("button", { name: /start interview/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The model is unavailable: boom",
    );
  });

  it("clears a previous error on the next attempt", async () => {
    const api = fakeApi({
      startSession: vi
        .fn()
        .mockRejectedValueOnce(new ApiError("Cannot reach the server."))
        .mockResolvedValue(session),
    });
    const user = userEvent.setup();
    render(<App api={api} />);

    await user.click(screen.getByRole("button", { name: /start interview/i }));
    await screen.findByRole("alert");

    await user.click(screen.getByRole("button", { name: /start interview/i }));

    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  });
});
