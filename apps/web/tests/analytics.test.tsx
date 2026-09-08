import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import {
  catalogSummary,
  deploymentCoverage,
  eventComposition,
  providerSummary,
} from "../lib/analytics";
import { CatalogAnalytics, BenchmarkRange } from "../components/analytics";
import type {
  Model,
  Provider,
  Deployment,
  MarketEvent,
  Benchmark,
} from "../lib/api";

const model = (overrides: Partial<Model> = {}): Model => ({
  id: "fixture",
  name: "Fixture",
  publisher: null,
  family: null,
  context_window: null,
  open_weights: null,
  release_date: null,
  identity_status: "resolved",
  deployment_count: 0,
  input_price_from: null,
  output_price_from: null,
  capabilities: [],
  facts: {},
  ...overrides,
});

it("keeps unknown and invalid prices out of the median but includes a real zero price", () => {
  const summary = catalogSummary([
    model(),
    model({ input_price_from: "0" }),
    model({ input_price_from: "2" }),
    model({ input_price_from: "bad" }),
  ]);
  expect(summary.priced).toBe(2);
  expect(summary.median).toBe(1);
  expect(catalogSummary([model()]).median).toBeNull();
  expect(catalogSummary([model({ input_price_from: "0" })]).median).toBe(0);
});

it("assigns every context boundary and unknown to exactly one bucket", () => {
  const summary = catalogSummary(
    [null, 31999, 32000, 127999, 128000, 999999, 1000000].map(
      (context_window) => model({ context_window }),
    ),
  );
  expect(summary.context.map((row) => row.value)).toEqual([1, 2, 2, 1, 1]);
  expect(summary.context.reduce((sum, row) => sum + row.value, 0)).toBe(
    summary.total,
  );
});

it("switches to capability evidence without implying unknown support is absent", () => {
  render(
    <CatalogAnalytics
      models={[model({ capabilities: ["reasoning", "tool_calling"] }), model()]}
      scope="Filtered page"
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Capabilities" }));
  expect(screen.getByText("Reasoning")).toBeInTheDocument();
  expect(screen.getByText(/missing support is unknown/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Capabilities" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(screen.getByText(/Filtered page/)).toBeInTheDocument();
});

it("uses all matching provider listings as the denominator even beyond the top five", () => {
  const providers = [1, 2, 3, 4, 5, 6, 0].map(
    (deployment_count, index): Provider => ({
      id: String(index),
      name: `Fixture ${index}`,
      kind: "direct",
      deployment_count,
      facts: {},
    }),
  );
  const summary = providerSummary(providers);
  expect(summary.total).toBe(21);
  expect(summary.active).toBe(6);
  expect(summary.leaders.map((row) => row.deployment_count)).toEqual([
    6, 5, 4, 3, 2,
  ]);
});

it("counts reported false and zero values as evidence, without counting null as coverage", () => {
  const deployments = [
    {
      facts: {
        "price.input_tokens": { value: 0 },
        availability: { value: false },
        context_window: { value: null },
      },
    },
    { facts: {} },
  ] as unknown as Deployment[];
  expect(deploymentCoverage(deployments).map((row) => row.value)).toEqual([
    1, 0, 0, 1,
  ]);
});

it("accounts for unfamiliar event types rather than silently dropping signals", () => {
  const events = [
    { event_type: "price_change" },
    { event_type: "price_change" },
    { event_type: "new_type" },
  ] as MarketEvent[];
  expect(eventComposition(events)).toEqual([
    { label: "price change", value: 2 },
    { label: "new type", value: 1 },
  ]);
});

it("never visualizes mixed benchmark methodologies as one distribution", () => {
  const rows = [
    {
      id: "a",
      comparable: true,
      score: "1",
      group_id: "first",
      metric: "elo",
      version: "v1",
      evaluator: "fixture",
    },
    {
      id: "b",
      comparable: true,
      score: "2",
      group_id: "second",
      metric: "win_rate",
      version: "v1",
      evaluator: "fixture",
    },
  ] as Benchmark[];
  const { container } = render(<BenchmarkRange rows={rows} />);
  expect(container).toBeEmptyDOMElement();
});
