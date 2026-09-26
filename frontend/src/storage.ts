const KEY = "interview-bot.session-id";

// Private browsing and blocked site data make these throw rather than no-op,
// and losing the id is never worth breaking the page over.
export function rememberSession(sessionId: string): void {
  try {
    localStorage.setItem(KEY, sessionId);
  } catch {
    /* the interview still works, it just will not resume */
  }
}

export function recallSession(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function forgetSession(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* nothing to clean up if it was never written */
  }
}
