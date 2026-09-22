import type { Difficulty, Grade, Question, Session, Topic } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {}

async function post<T>(path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body ?? {}),
    });
  } catch {
    throw new ApiError("Cannot reach the server. Is the backend running?");
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response));
  }
  return (await response.json()) as T;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const { detail } = await response.json();
    // FastAPI sends validation errors as a list of objects, not a string.
    if (typeof detail === "string") return detail;
  } catch {
    /* fall through to the status-based message */
  }
  return `Request failed with status ${response.status}`;
}

export const api = {
  startSession: (topic: Topic, difficulty: Difficulty) =>
    post<Session>("/sessions", { topic, difficulty }),

  nextQuestion: (sessionId: string) =>
    post<Question>(`/sessions/${sessionId}/questions`),

  submitAnswer: (sessionId: string, questionId: string, answer: string) =>
    post<Grade>(`/sessions/${sessionId}/answers`, {
      question_id: questionId,
      answer,
    }),
};

export type Api = typeof api;
