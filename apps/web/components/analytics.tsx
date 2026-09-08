"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, ScanLine } from "lucide-react";
import type {
  Model,
  Provider,
  Deployment,
  MarketEvent,
  Overview,
} from "@/lib/api";
import {
  catalogSummary,
  providerSummary,
  deploymentCoverage,
  eventComposition,
} from "@/lib/analytics";
import { money, date } from "@/lib/format";
import type { Benchmark } from "@/lib/api";

export function BenchmarkRange({ rows }: { rows: Benchmark[] }) {
  const valid = rows.filter(
    (row) => row.comparable && Number.isFinite(Number(row.score)),
  );
  if (
    valid.length < 2 ||
    new Set(
      valid.map(
        (row) =>
          `${row.group_id}/${row.metric}/${row.version}/${row.evaluator}`,
      ),
    ).size !== 1
  )
    return null;
  const scores = valid.map((row) => Number(row.score));
  const low = Math.min(...scores),
    high = Math.max(...scores);
  return (
    <section
      className="benchmark-range"
      aria-label="Reported score distribution"
    >
      <div>
        <span className="eyebrow">REPORTED RANGE · CURRENT PAGE</span>
        <h3>
          {low.toLocaleString()} – {high.toLocaleString()}{" "}
          <span className="muted">{valid[0].metric}</span>
        </h3>
        <p>
          {valid.length} observations from the same reported cohort.
          Source-extracted and unverified; a score is not a recommendation.
        </p>
      </div>
      <div
        className="range-track"
        role="img"
        aria-label={`${valid.length} reported scores range from ${low} to ${high} ${valid[0].metric}. Exact values and evidence are in the table below.`}
      >
        {scores.map((score, index) => (
          <i
            key={valid[index].id}
            style={{
              left: `${high === low ? 50 : 4 + ((score - low) / (high - low)) * 92}%`,
            }}
            title={`${valid[index].model_name}: ${score}`}
          />
        ))}
        <span>{low.toLocaleString()}</span>
        <span>{high.toLocaleString()}</span>
      </div>
    </section>
  );
}

export function Breakdown({
  rows,
  total,
  unit = "models",
}: {
  rows: { label: string; value: number; href?: string }[];
  total: number;
  unit?: string;
}) {
  return (
    <ol className="breakdown" aria-label={`Breakdown in ${unit}`}>
      {rows.map((row) => (
        <li key={row.label}>
          <div className="breakdown-label">
            {row.href ? (
              <Link href={row.href}>
                {row.label}
                <ArrowUpRight size={12} />
              </Link>
            ) : (
              <span>{row.label}</span>
            )}
            <strong>
              {row.value.toLocaleString()} <small>{unit}</small>
            </strong>
          </div>
          <div className="breakdown-track" aria-hidden="true">
            <span
              style={{
                width: `${total ? Math.min(100, (row.value / total) * 100) : 0}%`,
              }}
            />
          </div>
        </li>
      ))}
    </ol>
  );
}

export function IntelligenceBrief({ data }: { data: Overview }) {
  const successful = data.sources.filter((s) => s.status === "success").length;
  return (
    <section
      className="intelligence-brief"
      aria-label="Catalog intelligence brief"
    >
      <div className="brief-heading">
        <span className="eyebrow">
          <ScanLine size={14} /> THE INTELLIGENCE BRIEF
        </span>
        <span className="brief-edition">
          CURRENT CATALOG / SOURCE OBSERVATIONS
        </span>
      </div>
      <div className="brief-body">
        <div>
          <h2>
            A wider field.
            <br />
            <span>A clearer decision.</span>
          </h2>
          <p>
            {data.models.toLocaleString()} canonical models, connected to the
            evidence behind their capabilities and cost. Start with the
            landscape. Investigate the trade-offs.
          </p>
          <Link href="/models" className="brief-link">
            Explore the model landscape <ArrowUpRight size={16} />
          </Link>
        </div>
        <div className="brief-signal">
          <span className="eyebrow">EVIDENCE TO WATCH</span>
          <strong className="brief-number">
            {data.unresolved_models.toLocaleString()}
          </strong>
          <h3>identities awaiting resolution</h3>
          <p>
            Source listings are not always distinct models. Unresolved
            identities stay separate from the canonical catalog.
          </p>
          <Link href="/models?include_unresolved=true">
            Inspect source identities <ArrowUpRight size={13} />
          </Link>
        </div>
        <div className="brief-source">
          <span className="eyebrow">SOURCE CHECK</span>
          <strong>
            {successful}
            <span> / {data.sources.length}</span>
          </strong>
          <p>latest syncs successful</p>
          <div className="source-meter" aria-hidden="true">
            {data.sources.map((s) => (
              <i
                key={s.id}
                className={s.status === "success" ? "healthy" : "attention"}
              />
            ))}
          </div>
          <p>
            {successful === data.sources.length && data.sources.length
              ? "Inspect timestamps to assess freshness."
              : "Review source health before relying on freshness."}
          </p>
          <Link href="/data-health">
            Review data health <ArrowUpRight size={13} />
          </Link>
        </div>
      </div>
    </section>
  );
}

export function CatalogAnalytics({
  models,
  scope = "Current page",
}: {
  models: Model[];
  scope?: string;
}) {
  const [view, setView] = useState<"context" | "capabilities">("context");
  const data = catalogSummary(models);
  if (!models.length) return null;
  return (
    <section className="analytics-split" aria-label="Catalog analysis">
      <div className="analytics-story">
        <span className="eyebrow">
          {scope} · {data.total} MODELS
        </span>
        <h2>What can this selection do?</h2>
        <p>
          {data.priced} of {data.total} models have a listed input price.
          Compare serving evidence before choosing a deployment.
        </p>
        <div className="inline-metric">
          <strong>
            {data.median === null ? "Unknown" : money(String(data.median))}
          </strong>
          <span>
            Median listed input rate
            <br />
            USD / 1M tokens · {data.priced} priced models
          </span>
        </div>
      </div>
      <div className="analytics-plot">
        <div
          className="analytic-controls"
          role="group"
          aria-label="Catalog breakdown"
        >
          <button
            aria-pressed={view === "context"}
            onClick={() => setView("context")}
          >
            Context windows
          </button>
          <button
            aria-pressed={view === "capabilities"}
            onClick={() => setView("capabilities")}
          >
            Capabilities
          </button>
        </div>
        <Breakdown rows={data[view]} total={data.total} />
        <p className="analytics-note">
          {view === "context"
            ? "Context capacity, not a measure of quality. K = thousand; M = million tokens."
            : "Reported support only. A model can appear in several categories; missing support is unknown."}
        </p>
      </div>
    </section>
  );
}

export function ProviderAnalytics({ providers }: { providers: Provider[] }) {
  const data = providerSummary(providers);
  if (!data.active) return null;
  const lead = data.leaders[0];
  return (
    <section className="analytics-split" aria-label="Provider landscape">
      <div className="analytics-story">
        <span className="eyebrow">CURRENT SEARCH · ACCESS LANDSCAPE</span>
        <h2>Where the catalog is served.</h2>
        <div className="inline-metric">
          <strong>{data.total.toLocaleString()}</strong>
          <span>
            listings across
            <br />
            {data.active} matching providers
          </span>
        </div>
        <p>
          {lead.name} accounts for{" "}
          {((lead.deployment_count / data.total) * 100).toFixed(1)}% of these
          listings. Listing counts describe catalog breadth, not traffic or
          market share.
        </p>
      </div>
      <div className="analytics-plot">
        <h3>Largest catalogs in this selection</h3>
        <Breakdown
          total={data.total}
          unit="listings"
          rows={data.leaders.map((p) => ({
            label: p.name,
            value: p.deployment_count,
            href: `/providers/${encodeURIComponent(p.id)}`,
          }))}
        />
        <p className="analytics-note">
          Top five by listing count · bars share the total of all matching
          providers.
        </p>
      </div>
    </section>
  );
}

export function DeploymentAnalytics({
  deployments,
}: {
  deployments: Deployment[];
}) {
  if (!deployments.length) return null;
  return (
    <details className="coverage-details">
      <summary>
        <ScanLine size={16} />
        <span>How complete is the serving evidence?</span>
        <span className="muted">{deployments.length} loaded listings</span>
      </summary>
      <div className="coverage-body">
        <p>
          Available observations for these listings. Coverage does not imply
          freshness or verification; inspect each fact in the table.
        </p>
        <Breakdown
          total={deployments.length}
          unit="listings"
          rows={deploymentCoverage(deployments)}
        />
      </div>
    </details>
  );
}

export function SignalAnalytics({ events }: { events: MarketEvent[] }) {
  if (!events.length) return null;
  const dates = events.map((e) => e.detected_at).sort();
  const rows = eventComposition(events);
  return (
    <section className="panel signal-analysis">
      <span className="eyebrow">OBSERVATION MIX</span>
      <h2>What is changing?</h2>
      <p>
        {rows[0].value} of {events.length} loaded signals are {rows[0].label}{" "}
        events.
      </p>
      <Breakdown total={events.length} rows={rows} unit="signals" />
      <p className="analytics-note">
        {date(dates[0])} – {date(dates[dates.length - 1])}. Loaded feed only;
        not a complete period or a release timeline.
      </p>
    </section>
  );
}
