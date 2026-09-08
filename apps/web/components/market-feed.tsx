"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BellRing,
  ExternalLink,
  Flame,
  Minus,
  Search,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { api, type MarketEvent } from "@/lib/api";
import { marketChange } from "@/lib/market";
import { date, humanize } from "@/lib/format";
import {
  feedStats,
  featuredMove,
  searchFeed,
  sortFeed,
  trendingModels,
  type FeedSort,
  type FeaturedMove,
} from "@/lib/feed";
import { SignalAnalytics } from "./analytics";
import { Empty, ErrorState, SourceLink } from "./ui";

const TABS = [
  { name: "All signals", value: "" },
  { name: "New models", value: "new_model" },
  { name: "Price changes", value: "price_change" },
  { name: "Deployments", value: "new_deployment" },
  { name: "Capabilities", value: "capability_change" },
  { name: "Context", value: "context_change" },
];

function eventHref(event: MarketEvent): string | null {
  return event.model_id || event.entity_type === "model"
    ? `/models/${event.model_id ?? event.entity_id}`
    : null;
}

function announcementNote(event: MarketEvent): string {
  if (event.event_type === "new_model") return "Added to the catalog";
  if (event.event_type === "new_deployment") {
    return event.provider
      ? `New serving option on ${humanize(event.provider)}`
      : "New serving option discovered";
  }
  return "Source metadata updated";
}

function SignalRow({ event }: { event: MarketEvent }) {
  const change = marketChange(event);
  const kind =
    event.event_type === "new_model" || event.event_type === "new_deployment"
      ? "announcement"
      : "move";
  const href = eventHref(event);
  const name = event.model_name ?? event.title;
  const Icon =
    change.direction === "up"
      ? ArrowUpRight
      : change.direction === "down"
        ? ArrowDownRight
        : change.direction === "new"
          ? Sparkles
          : Minus;
  return (
    <article className={`signal-row ${kind} ${change.tone}`}>
      <span className={`signal-icon ${change.tone}`} aria-hidden>
        <Icon size={15} />
      </span>
      <div className="signal-main">
        <div className="signal-titleline">
          {href ? (
            <Link className="signal-name" href={href}>
              {name}
            </Link>
          ) : (
            <span className="signal-name">{name}</span>
          )}
          {event.importance === "high" && (
            <span className="signal-flag">
              <Flame size={9} /> High impact
            </span>
          )}
        </div>
        <p className="signal-sub">
          {kind === "move" && event.provider
            ? `${humanize(event.provider)} · `
            : ""}
          {kind === "announcement" ? announcementNote(event) : change.label}
        </p>
      </div>
      <div className="signal-change">
        {event.old_value != null ? (
          <span className="signal-values mono">
            <span className="signal-old">{change.oldLabel}</span>
            <ArrowRight size={12} aria-label="changed to" />
            <strong>{change.newLabel}</strong>
            {change.unit && <em className="signal-unit">{change.unit}</em>}
          </span>
        ) : null}
        {change.percentage && (
          <span
            className={`change-pill ${change.tone}`}
            title="Versus the previous observation"
          >
            {change.percentage}
          </span>
        )}
      </div>
      <div className="signal-stamp">
        <SourceLink source={event.source} url={event.source_url} />
        <time
          className="mono"
          dateTime={event.detected_at}
          title={event.detected_at}
        >
          {date(event.detected_at)}
        </time>
        {href && (
          <Link
            className="signal-open"
            href={href}
            aria-label={`Inspect ${name}`}
          >
            <ExternalLink size={12} />
          </Link>
        )}
      </div>
    </article>
  );
}

function FeaturedMoveCard({ featured }: { featured: FeaturedMove }) {
  const event = featured.event;
  const href = eventHref(event);
  const name = event.model_name ?? event.title;
  const down = featured.direction === "down";
  return (
    <section
      className={`featured-move ${down ? "positive" : "negative"}`}
      aria-label="Biggest move in this feed"
    >
      <div className="featured-head">
        <span className="featured-eyebrow">
          <Flame size={11} /> Biggest move in this feed
        </span>
        <span className={`badge ${down ? "good" : "warning"}`}>
          {down ? "Cheaper to run" : "Costs more to run"}
        </span>
      </div>
      <div className="featured-body">
        <div className="featured-identity">
          {href ? (
            <Link className="featured-name" href={href}>
              {name}
            </Link>
          ) : (
            <span className="featured-name">{name}</span>
          )}
          <p>
            {event.provider ? `${humanize(event.provider)} · ` : ""}
            {event.change_field ? humanize(event.change_field) : "price"}
          </p>
        </div>
        <div className="featured-numbers mono">
          <span className="featured-old">{featured.oldLabel}</span>
          <ArrowRight size={14} aria-label="changed to" />
          <strong>{featured.newLabel}</strong>
          {featured.unit && <em>{featured.unit}</em>}
        </div>
        <span
          className={`featured-delta mono ${down ? "positive" : "negative"}`}
          aria-label={`${featured.percentage} change`}
        >
          {featured.percentage}
        </span>
      </div>
      <div className="featured-foot">
        <SourceLink source={event.source} url={event.source_url} />
        <time dateTime={event.detected_at} title={event.detected_at}>
          {date(event.detected_at)}
        </time>
        {href && (
          <Link className="featured-inspect" href={href}>
            Inspect model <ArrowUpRight size={12} />
          </Link>
        )}
      </div>
    </section>
  );
}

function TrendingPanel({ events }: { events: MarketEvent[] }) {
  const trending = useMemo(() => trendingModels(events), [events]);
  if (trending.length === 0) return null;
  return (
    <section className="panel rail-panel">
      <header className="rail-head">
        <TrendingUp size={13} /> Trending in this feed
      </header>
      <ol className="rail-list">
        {trending.map((model, index) => (
          <li key={model.modelId}>
            <span className="rail-rank mono">{index + 1}</span>
            <Link className="rail-name" href={`/models/${model.modelId}`}>
              {model.name}
            </Link>
            <span className="rail-count">{model.count} signals</span>
            {model.bestDelta != null && (
              <span className="change-pill positive">
                {model.bestDelta.toFixed(1)}%
              </span>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

function FeedSkeleton() {
  return (
    <div className="signal-feed" aria-hidden>
      {[64, 42, 55, 36, 50, 45].map((width, index) => (
        <div className="signal-skeleton" key={index}>
          <span className="skeleton chip" />
          <span className="skeleton line" style={{ width: `${width}%` }} />
          <span className="skeleton pill" />
        </div>
      ))}
      <span className="sr-only">Loading market signals…</span>
    </div>
  );
}

export function MarketFeed() {
  const [type, setType] = useState("");
  const [limit, setLimit] = useState(50);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<FeedSort>("latest");
  const query = useQuery({
    queryKey: ["events", type, limit],
    queryFn: () =>
      api<MarketEvent[]>(
        `market-events?limit=${limit}${type ? `&event_type=${type}` : ""}`,
      ),
  });
  const events = useMemo(() => query.data ?? [], [query.data]);
  const stats = useMemo(() => feedStats(events), [events]);
  const featured = useMemo(() => featuredMove(events), [events]);
  const visible = useMemo(
    () => sortFeed(searchFeed(events, q), sort),
    [events, q, sort],
  );
  return (
    <>
      <div
        className="desk-stats"
        role="group"
        aria-label="Loaded feed statistics"
      >
        <div className="desk-stat">
          <span className="desk-label">Signals in feed</span>
          <span className="desk-value mono">{stats.total}</span>
          <span className="desk-meta">loaded observation window</span>
        </div>
        <div className="desk-stat">
          <span className="desk-label">Price drops</span>
          <span className="desk-value mono good">{stats.drops}</span>
          <span className="desk-meta">cheaper to run</span>
        </div>
        <div className="desk-stat">
          <span className="desk-label">New listings</span>
          <span className="desk-value mono">{stats.listings}</span>
          <span className="desk-meta">models and serving options</span>
        </div>
        <div className="desk-stat">
          <span className="desk-label">Value moves</span>
          <span className="desk-value mono">{stats.moves}</span>
          <span className="desk-meta">changed observations</span>
        </div>
      </div>
      <div className="feed-layout">
        <section className="feed-main" aria-label="Market signals">
          {featured && <FeaturedMoveCard featured={featured} />}
          <div className="feed-controls">
            <div className="tabs">
              {TABS.map((tab) => (
                <button
                  key={tab.value}
                  className={type === tab.value ? "active" : ""}
                  aria-pressed={type === tab.value}
                  onClick={() => setType(tab.value)}
                >
                  {tab.name}
                </button>
              ))}
            </div>
            <div className="feed-tools">
              <label className="feed-search">
                <Search size={13} aria-hidden />
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Filter by model or provider"
                  aria-label="Filter signals"
                />
              </label>
              <div className="feed-sort" role="group" aria-label="Sort signals">
                <button
                  aria-pressed={sort === "latest"}
                  onClick={() => setSort("latest")}
                >
                  Newest
                </button>
                <button
                  aria-pressed={sort === "movers"}
                  onClick={() => setSort("movers")}
                >
                  Movers
                </button>
              </div>
            </div>
          </div>
          {query.isPending ? (
            <FeedSkeleton />
          ) : query.error ? (
            <ErrorState error={query.error} retry={query.refetch} />
          ) : visible.length ? (
            <>
              <div className="signal-feed">
                {visible.map((event) => (
                  <SignalRow key={event.id} event={event} />
                ))}
              </div>
              {visible.length > 10 && !q && (
                <aside className="feed-cta">
                  <BellRing size={15} className="accent" />
                  <p>
                    <strong>Read the tape once</strong> — then let Fener watch
                    it for you. Watched models ping your Telegram the moment
                    their prices move.
                  </p>
                  <Link className="button small" href="/models">
                    Watch a model
                  </Link>
                </aside>
              )}
              {limit < 200 && (query.data?.length ?? 0) >= limit && (
                <button
                  className="button feed-more"
                  onClick={() => setLimit(Math.min(200, limit + 50))}
                >
                  Load more signals
                  <span className="mono">{visible.length} shown</span>
                </button>
              )}
            </>
          ) : q ? (
            <Empty title="Nothing matches that filter">
              Try a different model, provider or clear the filter to see the
              full tape.
            </Empty>
          ) : (
            <Empty title="No changes of this kind yet">
              Changes appear when successive source observations differ. Initial
              discovery is not a new release claim.
            </Empty>
          )}
        </section>
        <aside className="feed-rail" aria-label="Feed context">
          <SignalAnalytics events={events} />
          <TrendingPanel events={events} />
          <section className="panel rail-panel watch-cta">
            <header className="rail-head">
              <BellRing size={13} /> Never miss a drop
            </header>
            <p>
              Pick favourite models and Fener sends their price changes straight
              to your Telegram.
            </p>
            <Link className="button primary small" href="/models">
              Choose models to watch
            </Link>
          </section>
          <section className="rail-legend" aria-label="How to read the feed">
            <span>
              <i className="legend-dot positive" /> Lower prices / expanded
              capabilities
            </span>
            <span>
              <i className="legend-dot negative" /> Higher prices / reduced
              capabilities
            </span>
            <span>Discovery dates are not release dates.</span>
          </section>
        </aside>
      </div>
    </>
  );
}
