import { beforeEach, expect, it } from "vitest";
import { resetVisitBaseline, visitBaseline } from "../lib/since";

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  resetVisitBaseline();
});

it("returns the previous visit on the first call and records the current one", () => {
  localStorage.setItem("fener.lastVisit.v1", "2026-01-01T00:00:00.000Z");
  expect(visitBaseline()).toBe("2026-01-01T00:00:00.000Z");
  const recorded = localStorage.getItem("fener.lastVisit.v1") ?? "";
  expect(Number.isNaN(new Date(recorded).getTime())).toBe(false);
  expect(recorded).not.toBe("2026-01-01T00:00:00.000Z");
});

it("keeps one stable baseline for the whole browser session", () => {
  localStorage.setItem("fener.lastVisit.v1", "2026-01-01T00:00:00.000Z");
  const first = visitBaseline();
  // Simulate a later page navigation: the stored visit moved forward, but the
  // baseline for this session must stay pinned to the session start.
  localStorage.setItem("fener.lastVisit.v1", "2026-01-02T00:00:00.000Z");
  expect(visitBaseline()).toBe(first);
});

it("returns null on a brand new browser and the visit on the next session", () => {
  expect(visitBaseline()).toBeNull();
  resetVisitBaseline();
  sessionStorage.clear();
  expect(visitBaseline()).not.toBeNull();
});
