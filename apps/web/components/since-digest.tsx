"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Clock3 } from "lucide-react";
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
    <aside
      className="panel since-digest"
      aria-label="Changes since your last visit"
    >
      <div className="since-digest-head">
        <span className="since-digest-title">
          <Clock3 size={14} className="accent" />
          <strong>
            {events.length} market {events.length === 1 ? "change" : "changes"}{" "}
            since your last visit
          </strong>
        </span>
        <Link href="/market" className="since-digest-link">
          Open the feed
        </Link>
      </div>
      <ul className="since-digest-list">
        {events.slice(0, 3).map((event) => (
          <li key={event.id}>
            <span className="mono">{event.model_name ?? event.entity_id}</span>
            <span className="muted"> — {event.title}</span>
          </li>
        ))}
      </ul>
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
