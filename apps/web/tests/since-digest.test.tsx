import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import type { MarketEvent } from "../lib/api";
import { DigestCard } from "../components/since-digest";

function event(id: string, modelName: string | null): MarketEvent {
  const basis = { currency: "USD", quantity: 1_000_000, unit: "tokens" };
  return {
    id,
    event_type: "price_change",
    entity_type: "deployment",
    entity_id: `${id}-deployment`,
    model_id: modelName ? `${id}-model` : null,
    model_name: modelName,
    provider: "fixture-provider",
    title: "price input changed",
    change_field: "price.input_tokens",
    old_value: { ...basis, amount: "0.4" },
    new_value: { ...basis, amount: "0.2" },
    importance: "low",
    source: "fixture",
    source_url: "https://example.com/fixture",
    detected_at: "2026-01-01T00:00:00Z",
  };
}

it("shows the change count and readable model entries", () => {
  render(<DigestCard events={[event("1", "Alpha"), event("2", "Beta")]} />);
  expect(
    screen.getByText(/2 market changes since your last visit/),
  ).toBeInTheDocument();
  expect(screen.getByText("Alpha")).toBeInTheDocument();
  expect(screen.getByText("Beta")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open feed" })).toHaveAttribute(
    "href",
    "/market",
  );
});

it("uses the singular for one change and falls back to the entity id", () => {
  render(<DigestCard events={[event("3", null)]} />);
  expect(
    screen.getByText(/1 market change since your last visit/),
  ).toBeInTheDocument();
  expect(screen.getByText("3-deployment")).toBeInTheDocument();
});

it("renders nothing when there is nothing new", () => {
  const { container } = render(<DigestCard events={[]} />);
  expect(container).toBeEmptyDOMElement();
});
