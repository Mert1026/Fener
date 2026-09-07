const VISIT_KEY = "fener.lastVisit.v1";
const BASELINE_KEY = "fener.visitBaseline.v1";
const SESSION_FLAG = "fener.visitOpen";

let cached: string | null | undefined;

/**
 * Timestamp of the previous app visit, stable for the whole browser session.
 * The first call in a session reads the previous visit from localStorage,
 * records the current visit, and stashes the baseline so that navigating
 * between pages keeps one consistent "since your last visit" window.
 * Returns null when there is no previous visit or storage is unavailable.
 */
export function visitBaseline(): string | null {
  if (typeof window === "undefined") return null;
  if (cached !== undefined) return cached;
  try {
    if (sessionStorage.getItem(SESSION_FLAG) === "1") {
      cached = sessionStorage.getItem(BASELINE_KEY) || null;
      return cached;
    }
    const previous = localStorage.getItem(VISIT_KEY);
    cached = previous;
    sessionStorage.setItem(BASELINE_KEY, previous ?? "");
    sessionStorage.setItem(SESSION_FLAG, "1");
    localStorage.setItem(VISIT_KEY, new Date().toISOString());
  } catch {
    cached = null; // storage unavailable: the digest quietly disables itself
  }
  return cached;
}

/** Forget the in-memory session baseline (used by tests). */
export function resetVisitBaseline(): void {
  cached = undefined;
}
