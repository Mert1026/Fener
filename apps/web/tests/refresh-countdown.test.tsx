import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { RefreshCountdown } from "../components/refresh-countdown";

function renderWithClient() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const invalidate = vi.spyOn(client, "invalidateQueries");
  render(
    <QueryClientProvider client={client}>
      <RefreshCountdown />
    </QueryClientProvider>,
  );
  return invalidate;
}

afterEach(() => {
  vi.useRealTimers();
});

it("shows the full period before the first refresh", () => {
  vi.useFakeTimers();
  renderWithClient();
  expect(screen.getByRole("timer").textContent).toContain("NEXT SYNC 1:00");
});

it("counts down and refreshes the workspace when it reaches zero", () => {
  vi.useFakeTimers();
  const invalidate = renderWithClient();
  act(() => {
    vi.advanceTimersByTime(45_000);
  });
  expect(screen.getByRole("timer").textContent).toContain("0:15");
  expect(invalidate).not.toHaveBeenCalled();
  act(() => {
    vi.advanceTimersByTime(15_000);
  });
  expect(invalidate).toHaveBeenCalledTimes(1);
  act(() => {
    vi.advanceTimersByTime(1_000);
  });
  expect(screen.getByRole("timer").textContent).toContain("NEXT SYNC 0:59");
});
