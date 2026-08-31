import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";
import { ModelTable } from "../components/model-table";
import type { Model } from "../lib/api";
const models: Model[] = [
  {
    id: "fixture-one",
    name: "Fixture One",
    publisher: "Test publisher",
    family: null,
    context_window: null,
    open_weights: null,
    release_date: null,
    identity_status: "resolved",
    deployment_count: 1,
    input_price_from: "0",
    input_price_evidence: {
      id: "price-fixture",
      value: {
        amount: "0",
        currency: "USD",
        quantity: 1000000,
        unit: "tokens",
      },
      source: "fixture",
      source_url: "https://example.com/fixture",
      observed_at: "2026-08-31T00:00:00Z",
      last_seen_at: "2026-08-31T00:00:00Z",
      verification: "test",
      stale: false,
    },
    output_price_from: null,
    capabilities: [],
    facts: {},
  },
];
beforeEach(() => localStorage.clear());
it("lets the user select a model for comparison and distinguishes free from unknown", () => {
  render(<ModelTable models={models} />);
  expect(screen.getByText("$0")).toBeInTheDocument();
  const checkbox = screen.getByRole("checkbox", {
    name: "Compare Fixture One",
  });
  fireEvent.click(checkbox);
  expect(checkbox).toBeChecked();
  expect(
    JSON.parse(localStorage.getItem("fener.compare.v1") ?? "[]")[0].id,
  ).toBe("fixture-one");
});
it("lets the user configure table columns", () => {
  render(<ModelTable models={models} />);
  fireEvent.click(screen.getByText("Columns"));
  const checkbox = screen.getByRole("checkbox", { name: "Publisher" });
  fireEvent.click(checkbox);
  expect(
    screen.getByRole("columnheader", { name: /Publisher/ }),
  ).toBeInTheDocument();
});
