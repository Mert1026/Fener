import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const sourcesFixture = vi.fn(async () => [
  {
    id: "source-a",
    last_success_at: new Date(Date.now() - 3_600_000).toISOString(),
    interval_seconds: 21_600,
  },
  { id: "source-b", last_success_at: null, interval_seconds: 21_600 },
]);

vi.mock("../lib/api", () => ({
  api: () => sourcesFixture(),
}));

const { RefreshCountdown } = await import("../components/refresh-countdown");

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

beforeEach(() => {
  sourcesFixture.mockClear();
});

it("counts down to the soonest source sync window", async () => {
  renderWithClient();
  // One source succeeded 1h ago on a 6h interval: due in 5h exactly.
  await waitFor(() =>
    expect(screen.getByRole("timer").textContent).toMatch(
      /NEXT SYNC 4:59:5[89]|NEXT SYNC 5:00:00/,
    ),
  );
});

it("shows LIVE when no schedule is available", async () => {
  sourcesFixture.mockResolvedValueOnce([]);
  renderWithClient();
  await waitFor(() =>
    expect(screen.getByRole("timer").textContent).toContain("LIVE"),
  );
});

it("refreshes the workspace exactly once per elapsed window", async () => {
  sourcesFixture.mockResolvedValue([
    {
      id: "source-a",
      last_success_at: new Date(Date.now() - 7 * 3_600_000).toISOString(),
      interval_seconds: 21_600,
    },
  ]);
  const invalidate = renderWithClient();
  await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(1));
  // Several countdown ticks later: still exactly one refresh for this window.
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 1_200));
  });
  expect(invalidate).toHaveBeenCalledTimes(1);
});
