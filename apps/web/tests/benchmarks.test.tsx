import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, it, vi } from "vitest";
import BenchmarksPage from "../app/benchmarks/page";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: vi.fn(), isPrivateLocked: () => false }));

const emptyState = {
  configured: true,
  model: "fixture-model",
  refresh: null,
};

beforeEach(() => {
  vi.mocked(api).mockReset();
});

it("queues one approved update for the whole catalog without a manual prompt", async () => {
  vi.mocked(api).mockImplementation(async (path, options) => {
    if (path === "benchmark-refresh" && options?.method === "POST") {
      return {
        ...emptyState,
        refresh: {
          id: "fixture-refresh",
          status: "queued",
          total_models: 363,
          processed_models: 0,
          imported_results: 0,
          failed_models: 0,
          current_model: null,
          error: null,
          item_status_counts: { queued: 363 },
          models_without_results: 0,
          failure_reasons: [],
        },
      };
    }
    if (path === "benchmark-refresh") return emptyState;
    if (path === "benchmarks/groups") return [];
    throw new Error(`Unexpected API path: ${path}`);
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <BenchmarksPage />
    </QueryClientProvider>,
  );

  const button = await screen.findByRole("button", {
    name: "Update all benchmarks",
  });
  await waitFor(() => expect(button).toBeEnabled());
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(screen.getByText(/does not spend Z.ai tokens/)).toBeInTheDocument();
  fireEvent.click(button);

  await waitFor(() => {
    const post = vi
      .mocked(api)
      .mock.calls.find(([, options]) => options?.method === "POST");
    expect(post).toBeDefined();
    expect(JSON.parse(post![1]!.body as string)).toMatchObject({
      acknowledge_cost: true,
      request_id: expect.any(String),
    });
  });
  await waitFor(() => expect(button).toBeDisabled());
  expect(screen.getByText(/0 \/ 363 models/)).toBeInTheDocument();
});

it("explains a completed run that stored no benchmark results", async () => {
  vi.mocked(api).mockImplementation(async (path) => {
    if (path === "benchmark-refresh")
      return {
        configured: true,
        model: "fixture-model",
        refresh: {
          id: "finished-refresh",
          status: "completed_with_errors",
          total_models: 363,
          processed_models: 363,
          imported_results: 0,
          failed_models: 302,
          current_model: null,
          error: null,
          item_status_counts: { failed: 284, uncertain: 18, success: 61 },
          models_without_results: 61,
          failure_reasons: [
            {
              message:
                "No complete usable cited benchmark response was returned.",
              count: 284,
            },
          ],
        },
      };
    if (path === "benchmarks/groups") return [];
    throw new Error(`Unexpected API path: ${path}`);
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <BenchmarksPage />
    </QueryClientProvider>,
  );

  expect(
    await screen.findByText("Update finished with no usable benchmark claims"),
  ).toBeInTheDocument();
  expect(screen.getByText(/284 rejected by validation/)).toBeInTheDocument();
  expect(screen.getByText(/Nothing is hidden/)).toBeInTheDocument();
});

it("offers to resume a refresh paused by provider rate limits", async () => {
  vi.mocked(api).mockImplementation(async (path) => {
    if (path === "benchmark-refresh")
      return {
        configured: true,
        model: "fixture-model",
        refresh: {
          id: "paused-refresh",
          status: "paused",
          total_models: 431,
          processed_models: 60,
          imported_results: 0,
          failed_models: 46,
          current_model: null,
          error:
            "Z.ai rate limit reached. Wait before pressing Resume benchmarks.",
          item_status_counts: { failed: 46, no_evidence: 14, queued: 371 },
          models_without_results: 14,
          failure_reasons: [],
        },
      };
    if (path === "benchmarks/groups") return [];
    throw new Error(`Unexpected API path: ${path}`);
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <BenchmarksPage />
    </QueryClientProvider>,
  );

  expect(
    await screen.findByRole("button", { name: "Resume benchmarks" }),
  ).toBeEnabled();
  expect(screen.getByText(/Z.ai rate limit reached/)).toBeInTheDocument();
});
