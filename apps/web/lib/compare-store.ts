"use client";
import { useMemo, useSyncExternalStore } from "react";
type Item = { id: string; name: string };
const key = "fener.compare.v1";
function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("fener-compare", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("fener-compare", callback);
  };
}
function snapshot() {
  return localStorage.getItem(key) ?? "[]";
}
export function useCompare() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => "[]");
  const selected = useMemo<Item[]>(() => {
    try {
      return JSON.parse(raw).slice(0, 6);
    } catch {
      return [];
    }
  }, [raw]);
  function toggle(item: Item) {
    const next = selected.some((x) => x.id === item.id)
      ? selected.filter((x) => x.id !== item.id)
      : [...selected, item].slice(0, 6);
    localStorage.setItem(key, JSON.stringify(next));
    window.dispatchEvent(new Event("fener-compare"));
  }
  function clear() {
    localStorage.setItem(key, "[]");
    window.dispatchEvent(new Event("fener-compare"));
  }
  return { selected, toggle, clear };
}
