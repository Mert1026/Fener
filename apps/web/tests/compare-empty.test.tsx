import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import ComparePage from "../app/compare/page";
import { api } from "../lib/api";
vi.mock("../lib/api", () => ({ api: vi.fn() }));
vi.mock("../components/since-digest", () => ({ SinceDigest: () => null }));
vi.mock("../lib/compare-store", () => ({
  useCompare: () => ({
    selected: [
      { id: "fixture-a", name: "Fixture A" },
      { id: "fixture-b", name: "Fixture B" },
    ],
    toggle: vi.fn(),
  }),
}));

it("explains unavailable serving options instead of offering a no-op calculation", async () => {
  vi.mocked(api).mockImplementation(async (path) => ({
    model: {
      id: path,
      name: path,
      publisher: null,
      context_window: null,
      facts: {},
      capabilities: [],
      open_weights: null,
    },
    deployments: [],
  }));
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <ComparePage />
    </QueryClientProvider>,
  );
  const button = await screen.findByRole("button", { name: "Calculate costs" });
  expect(button).toBeDisabled();
  expect(
    screen.getByText(/No serving deployments are available/),
  ).toBeInTheDocument();
});
