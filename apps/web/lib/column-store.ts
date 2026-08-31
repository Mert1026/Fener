"use client";
import { useMemo, useSyncExternalStore } from "react";
import type { Updater, VisibilityState } from "@tanstack/react-table";
const key = "fener.columns.v1";
const fallback = '{"publisher":false}';
function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("fener-columns", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("fener-columns", callback);
  };
}
function snapshot() {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}
export function useColumns() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => fallback);
  const visibility = useMemo<VisibilityState>(() => {
    try {
      const parsed = JSON.parse(raw);
      return Object.fromEntries(
        Object.entries(parsed).filter(
          ([, value]) => typeof value === "boolean",
        ),
      ) as VisibilityState;
    } catch {
      return { publisher: false };
    }
  }, [raw]);
  function setVisibility(update: Updater<VisibilityState>) {
    const next = typeof update === "function" ? update(visibility) : update;
    localStorage.setItem(key, JSON.stringify(next));
    window.dispatchEvent(new Event("fener-columns"));
  }
  return { visibility, setVisibility };
}
