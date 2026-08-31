import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, it, vi } from "vitest";
import ResearchPage from "../app/research/page";
import { api } from "../lib/api";

vi.mock("../lib/api", () => ({ api: vi.fn(), isPrivateLocked: () => false }));
const config = {
  configured: false,
  provider: "zai",
  provider_name: "Z.ai",
  key_env: "ZAI_API_KEY",
  request_limits: "1 web search and 1 summary, up to 2,000 output tokens",
  source_policy: "Only approved-domain excerpts are summarized.",
  model: "fixture-model",
  daily_limit: 5,
  domains: ["openai.com"],
  runs: [],
};

beforeEach(() => vi.mocked(api).mockReset());
function renderResearch(
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  }),
) {
  return render(
    <QueryClientProvider client={client}>
      <ResearchPage />
    </QueryClientProvider>,
  );
}

it("shows local setup instructions and cannot submit without a provider key", async () => {
  vi.mocked(api).mockResolvedValue(config);
  renderResearch();
  expect(await screen.findByText("API key needed")).toBeInTheDocument();
  expect(screen.getByText("ZAI_API_KEY")).toBeInTheDocument();
  expect(screen.queryByText("OPENAI_API_KEY")).not.toBeInTheDocument();
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

it("invalidates approval when refreshed provider configuration changes", async () => {
  const client = new QueryClient();
  vi.mocked(api).mockResolvedValue({ ...config, configured: true });
  renderResearch(client);
  await screen.findByText("Ready");
  fireEvent.change(screen.getByLabelText("What should we investigate?"), {
    target: { value: "Check the fixture source claim" },
  });
  fireEvent.click(screen.getByRole("checkbox"));
  expect(
    screen.getByRole("button", { name: "Run cited research" }),
  ).toBeEnabled();
  await act(async () => {
    client.setQueryData(["research"], {
      ...config,
      configured: true,
      provider: "openai",
      provider_name: "OpenAI",
      model: "other-model",
    });
  });
  await waitFor(() => expect(screen.getByRole("checkbox")).not.toBeChecked());
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
    provider: "zai",
    model: "fixture-model",
    query: "Check a different fixture benchmark",
    acknowledge_cost: true,
    request_id: expect.any(String),
  });
});
