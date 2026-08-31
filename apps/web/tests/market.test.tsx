import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import type { MarketEvent } from "../lib/api";
import { marketChange } from "../lib/market";
import { EventList } from "../components/event-list";

function event(before: string, after: string): MarketEvent {
  const basis = { currency: "USD", quantity: 1_000_000, unit: "tokens" };
  return {
    id: "fixture",
    event_type: "price_change",
    entity_type: "deployment",
    entity_id: "fixture-deployment",
    model_id: "fixture-model",
    model_name: "Fixture model",
    provider: "fixture-provider",
    title: "Fixture price",
    change_field: "price.input_tokens",
    old_value: { ...basis, amount: before },
    new_value: { ...basis, amount: after },
    importance: "low",
    source: "fixture",
    source_url: "https://example.com/fixture",
    detected_at: "2026-01-01T00:00:00Z",
  };
}

it("uses numerical rates and identifies cheaper vs more expensive prices", () => {
  expect(marketChange(event("0.2", "0.2000000"))).toMatchObject({
    oldLabel: "$0.2",
    newLabel: "$0.2",
    direction: "flat",
    percentage: "0%",
  });
  expect(marketChange(event("0.4", "0.2"))).toMatchObject({
    direction: "down",
    tone: "positive",
    percentage: "-50%",
  });
  expect(marketChange(event("0.2", "0.4"))).toMatchObject({
    direction: "up",
    tone: "negative",
    percentage: "+100%",
  });
  expect(marketChange(event("0", "0.1")).percentage).toBeNull();
});

it("preserves meaningful small changes and normalizes billing quantities", () => {
  const change = marketChange(
    event("0.200000000000000000001", "0.200000000000000000002"),
  );
  expect(change.direction).toBe("up");
  expect(change.oldLabel).not.toBe(change.newLabel);
  expect(change.percentage).not.toBe("0%");
  const scaled = event("0.0000002", "0.2");
  scaled.old_value = {
    amount: "0.0000002",
    quantity: 1,
    currency: "USD",
    unit: "tokens",
  };
  expect(marketChange(scaled).direction).toBe("flat");
});

it("renders readable cards with source links and direction instead of raw JSON", () => {
  const { container } = render(
    <EventList events={[event("0.4", "0.2")]} full />,
  );
  expect(screen.getByText("$0.4")).toBeInTheDocument();
  expect(screen.getByText("$0.2")).toBeInTheDocument();
  expect(screen.getByLabelText("down")).toBeInTheDocument();
  expect(screen.getByText("-50%")).toBeInTheDocument();
  expect(container.textContent).not.toContain('"amount"');
  expect(screen.getByRole("link", { name: "fixture" })).toHaveAttribute(
    "href",
    "https://example.com/fixture",
  );
});
