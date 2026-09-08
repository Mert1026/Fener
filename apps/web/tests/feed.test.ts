import { expect, it } from "vitest";
import type { MarketEvent } from "../lib/api";
import {
  feedStats,
  featuredMove,
  searchFeed,
  sortFeed,
  trendingModels,
} from "../lib/feed";

const basis = { currency: "USD", quantity: 1_000_000, unit: "tokens" };

function event(overrides: Partial<MarketEvent> & { id: string }): MarketEvent {
  return {
    event_type: "price_change",
    entity_type: "deployment",
    entity_id: `${overrides.id}-dep`,
    model_id: `${overrides.id}-model`,
    model_name: `Model ${overrides.id}`,
    provider: "openrouter",
    title: "price input changed",
    change_field: "price.input_tokens",
    old_value: { ...basis, amount: "0.4" },
    new_value: { ...basis, amount: "0.2" },
    importance: "low",
    source: "models_dev",
    source_url: "https://example.com/feed",
    detected_at: "2026-01-01T00:00:00Z",
    ...overrides,
  } as MarketEvent;
}

it("summarizes the loaded feed honestly", () => {
  const stats = feedStats([
    event({ id: "drop" }),
    event({
      id: "rise",
      old_value: { ...basis, amount: "0.1" },
      new_value: { ...basis, amount: "0.3" },
    }),
    event({
      id: "model",
      event_type: "new_model",
      old_value: null,
      new_value: null,
    }),
    event({
      id: "dep",
      event_type: "new_deployment",
      old_value: null,
      new_value: null,
    }),
  ]);
  expect(stats).toEqual({ total: 4, drops: 1, listings: 2, moves: 2 });
});

it("features the largest real move regardless of direction", () => {
  const featured = featuredMove([
    event({ id: "drop" }),
    event({
      id: "rise",
      old_value: { ...basis, amount: "0.1" },
      new_value: { ...basis, amount: "0.3" },
      detected_at: "2026-01-02T00:00:00Z",
    }),
    event({
      id: "listing",
      event_type: "new_deployment",
      old_value: null,
      new_value: null,
    }),
  ]);
  expect(featured?.direction).toBe("up");
  expect(featured?.percentage).toBe("+200%");
  expect(featured?.newLabel).toBe("$0.3");
});

it("returns no featured card when prices did not really move", () => {
  expect(
    featuredMove([
      event({ id: "flat", old_value: { ...basis, amount: "0.2" } }),
    ]),
  ).toBeNull();
});

it("ranks trending models by signal count and best drop", () => {
  const trending = trendingModels([
    event({ id: "a" }),
    event({ id: "a", detected_at: "2026-01-02T00:00:00Z" }),
    event({ id: "b" }),
  ]);
  expect(trending[0]).toMatchObject({ modelId: "a-model", count: 2 });
  expect(trending[0].bestDelta).not.toBeNull();
  expect(trending[1]).toMatchObject({ modelId: "b-model", count: 1 });
});

it("sorts by magnitude in movers mode and by recency in latest mode", () => {
  const events = [
    event({
      id: "small",
      old_value: { ...basis, amount: "0.2" },
      new_value: { ...basis, amount: "0.22" },
      detected_at: "2026-01-03T00:00:00Z",
    }),
    event({
      id: "big",
      old_value: { ...basis, amount: "0.1" },
      new_value: { ...basis, amount: "0.3" },
      detected_at: "2026-01-01T00:00:00Z",
    }),
  ];
  expect(sortFeed(events, "movers").map((row) => row.id)).toEqual([
    "big",
    "small",
  ]);
  expect(sortFeed(events, "latest").map((row) => row.id)).toEqual([
    "small",
    "big",
  ]);
});

it("filters by model, provider and title without a needle when empty", () => {
  const events = [event({ id: "a" }), event({ id: "b", provider: "together" })];
  expect(searchFeed(events, "together").map((row) => row.id)).toEqual(["b"]);
  expect(searchFeed(events, "model a").map((row) => row.id)).toEqual(["a"]);
  expect(searchFeed(events, "  ")).toHaveLength(2);
});
