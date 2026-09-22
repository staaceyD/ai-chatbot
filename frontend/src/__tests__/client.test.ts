import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../api/client";

function mockFetch(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const spy = vi.fn().mockResolvedValue({ ok: true, status: 200, ...response });
  vi.stubGlobal("fetch", spy);
  return spy;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("startSession", () => {
  it("posts the topic and difficulty", async () => {
    const fetchSpy = mockFetch({
      json: async () => ({ session_id: "s1", topic: "python", difficulty: "mid" }),
    });

    const session = await api.startSession("python", "mid");

    expect(session.session_id).toBe("s1");
    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("http://localhost:8000/sessions");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ topic: "python", difficulty: "mid" });
  });
});

describe("submitAnswer", () => {
  it("sends the question id and answer in snake_case", async () => {
    const fetchSpy = mockFetch({
      json: async () => ({ score: 3, verdict: "ok", covered: [], missed: [] }),
    });

    await api.submitAnswer("s1", "q1", "my answer");

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("http://localhost:8000/sessions/s1/answers");
    expect(JSON.parse(init.body)).toEqual({ question_id: "q1", answer: "my answer" });
  });
});

describe("error handling", () => {
  it("surfaces the detail string from the backend", async () => {
    mockFetch({
      ok: false,
      status: 502,
      json: async () => ({ detail: "The model is unavailable: boom" }),
    });

    await expect(api.nextQuestion("s1")).rejects.toThrow(ApiError);
    await expect(api.nextQuestion("s1")).rejects.toThrow("The model is unavailable: boom");
  });

  it("falls back to the status when detail is not a string", async () => {
    mockFetch({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ msg: "must not be blank" }] }),
    });

    await expect(api.nextQuestion("s1")).rejects.toThrow("status 422");
  });

  it("falls back to the status when the body is not json", async () => {
    mockFetch({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    });

    await expect(api.nextQuestion("s1")).rejects.toThrow("status 500");
  });

  it("explains a connection failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    await expect(api.startSession("react", "mid")).rejects.toThrow(
      "Cannot reach the server",
    );
  });
});
