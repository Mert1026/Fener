import type { MarketEvent } from "./api";
import { marketChange } from "./market";

export type FeedSort = "latest" | "movers";

export type FeedStats = {
  total: number;
  drops: number;
  listings: number;
  moves: number;
};

export type FeaturedMove = {
  event: MarketEvent;
  percentage: string;
  direction: "up" | "down";
  oldLabel: string;
  newLabel: string;
  unit: string;
  magnitude: number;
};

export type TrendingModel = {
  modelId: string;
  name: string;
  count: number;
  bestDelta: number | null;
};

/** Headline numbers for the desk strip, computed from the loaded feed only. */
export function feedStats(events: MarketEvent[]): FeedStats {
  let drops = 0;
  let listings = 0;
  let moves = 0;
  for (const event of events) {
    const change = marketChange(event);
    if (
      event.event_type === "new_model" ||
      event.event_type === "new_deployment"
    ) {
      listings += 1;
    } else {
      moves += 1;
    }
    if (event.event_type === "price_change" && change.direction === "down") {
      drops += 1;
    }
  }
  return { total: events.length, drops, listings, moves };
}

/** The largest single price move in the feed, if any real move exists. */
export function featuredMove(events: MarketEvent[]): FeaturedMove | null {
  let best: FeaturedMove | null = null;
  for (const event of events) {
    if (event.event_type !== "price_change") continue;
    const change = marketChange(event);
    if (
      change.magnitude == null ||
      change.magnitude === 0 ||
      (change.direction !== "up" && change.direction !== "down")
    ) {
      continue;
    }
    if (!best || change.magnitude > best.magnitude) {
      best = {
        event,
        percentage: change.percentage ?? "",
        direction: change.direction,
        oldLabel: change.oldLabel,
        newLabel: change.newLabel,
        unit: change.unit,
        magnitude: change.magnitude,
      };
    }
  }
  return best;
}

/** Models mentioned most in the loaded feed, with their best price delta. */
export function trendingModels(
  events: MarketEvent[],
  cap = 5,
): TrendingModel[] {
  const byModel = new Map<string, TrendingModel>();
  for (const event of events) {
    const modelId = event.model_id ?? event.entity_id;
    const name = event.model_name ?? event.title;
    const existing = byModel.get(modelId);
    const delta =
      event.event_type === "price_change" &&
      marketChange(event).direction === "down"
        ? marketChange(event).magnitude
        : null;
    if (existing) {
      existing.count += 1;
      if (
        delta != null &&
        (existing.bestDelta == null || delta > existing.bestDelta)
      ) {
        existing.bestDelta = delta;
      }
    } else {
      byModel.set(modelId, {
        modelId,
        name,
        count: 1,
        bestDelta: delta,
      });
    }
  }
  return [...byModel.values()]
    .sort(
      (a, b) =>
        b.count - a.count ||
        (b.bestDelta ?? -1) - (a.bestDelta ?? -1) ||
        a.name.localeCompare(b.name),
    )
    .slice(0, cap);
}

export function searchFeed(events: MarketEvent[], q: string): MarketEvent[] {
  const needle = q.trim().toLowerCase();
  if (!needle) return events;
  return events.filter((event) =>
    [event.model_name, event.provider, event.title, event.entity_id]
      .filter((field): field is string => typeof field === "string")
      .some((field) => field.toLowerCase().includes(needle)),
  );
}

export function sortFeed(events: MarketEvent[], sort: FeedSort): MarketEvent[] {
  if (sort === "latest") {
    return [...events].sort((a, b) =>
      b.detected_at.localeCompare(a.detected_at),
    );
  }
  return [...events].sort((a, b) => {
    const magnitudeA = marketChange(a).magnitude ?? -1;
    const magnitudeB = marketChange(b).magnitude ?? -1;
    return (
      magnitudeB - magnitudeA || b.detected_at.localeCompare(a.detected_at)
    );
  });
}
