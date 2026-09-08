"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { api, type MarketEvent } from "@/lib/api";
import { visitBaseline } from "@/lib/since";

const SCOPE_FILTERS = {
  all: () => true,
  models: (event: MarketEvent) => event.model_id !== null,
  deployments: (event: MarketEvent) => event.entity_type === "deployment",
} as const;

export type DigestScope = keyof typeof SCOPE_FILTERS;

export function DigestCard({ events }: { events: MarketEvent[] }) {
  if (events.length === 0) return null;
  return (
    <aside className="digest-tape" aria-label="Changes since your last visit">
      <span className="digest-chip mono" aria-hidden>
        {events.length}
      </span>
      <strong className="digest-label">
        {events.length} market {events.length === 1 ? "change" : "changes"}{" "}
        since your last visit
      </strong>
      <span className="digest-items">
        {events.slice(0, 3).map((event) => (
          <Link
            key={event.id}
            className="digest-item"
            href={event.model_id ? `/models/${event.model_id}` : "/market"}
          >
            <span className="mono">{event.model_name ?? event.entity_id}</span>
            <span>{event.title}</span>
          </Link>
        ))}
      </span>
      <Link className="digest-link" href="/market">
        Open feed <ArrowUpRight size={12} />
      </Link>
    </aside>
  );
}

export function SinceDigest({ scope = "all" }: { scope?: DigestScope }) {
  const since = visitBaseline();
  const query = useQuery({
    queryKey: ["since-digest", since],
    queryFn: () =>
      api<MarketEvent[]>(
        `market-events?limit=50&since=${encodeURIComponent(since ?? "")}`,
      ),
    enabled: Boolean(since),
    staleTime: 60_000,
    retry: false,
  });
  if (!since || query.isPending || query.isError) return null;
  const events = (query.data ?? []).filter(SCOPE_FILTERS[scope]);
  return <DigestCard events={events} />;
}
