import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, it, vi } from "vitest";
import ResearchPage from "../app/research/page";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: vi.fn(), isPrivateLocked: () => false }));
const config = {
  configured: false,
  model: "fixture-model",
  daily_limit: 5,
  domains: ["openai.com"],
  runs: [],
};

beforeEach(() => vi.mocked(api).mockReset());
function renderResearch() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      <ResearchPage />
    </QueryClientProvider>,
  );
}

it("shows local setup instructions and cannot submit without a provider key", async () => {
  vi.mocked(api).mockResolvedValue(config);
  renderResearch();
  expect(await screen.findByText("API key needed")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("What should we investigate?"), {
    target: { value: "Check fixture benchmark methodology" },
  });
  fireEvent.click(screen.getByRole("checkbox"));
  expect(
    screen.getByRole("button", { name: "Run cited research" }),
  ).toBeDisabled();
  expect(
    vi
      .mocked(api)
      .mock.calls.every(([, options]) => options?.method !== "POST"),
  ).toBe(true);
});

it("requires approval for the current question and submits one explicit request", async () => {
  vi.mocked(api).mockResolvedValue({ ...config, configured: true });
  renderResearch();
  await screen.findByText("Ready");
  const question = screen.getByLabelText("What should we investigate?");
  fireEvent.change(question, {
    target: { value: "Check fixture benchmark methodology" },
  });
  const button = screen.getByRole("button", { name: "Run cited research" });
  expect(button).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox"));
  expect(button).toBeEnabled();
  fireEvent.change(question, {
    target: { value: "Check a different fixture benchmark" },
  });
  expect(button).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(button);
  await waitFor(() =>
    expect(
      vi
        .mocked(api)
        .mock.calls.filter(([, options]) => options?.method === "POST"),
    ).toHaveLength(1),
  );
  const submitted = vi
    .mocked(api)
    .mock.calls.find(([, options]) => options?.method === "POST")![1]!;
  expect(JSON.parse(submitted.body as string)).toMatchObject({
    query: "Check a different fixture benchmark",
    acknowledge_cost: true,
    request_id: expect.any(String),
  });
});
