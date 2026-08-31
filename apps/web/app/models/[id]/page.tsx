"use client";
import { use, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowLeftRight, Info } from "lucide-react";
import {
  api,
  type ModelDetail,
  type MarketEvent,
  type Benchmark,
} from "@/lib/api";
import { date, humanize, tokens } from "@/lib/format";
import { useCompare } from "@/lib/compare-store";
import { DeploymentTable } from "@/components/deployment-table";
import { EventList } from "@/components/event-list";
import {
  Badge,
  Empty,
  ErrorState,
  EvidenceValue,
  Footnote,
  Loading,
  SourceLink,
} from "@/components/ui";
const PriceHistoryChart = dynamic(
  () => import("@/components/chart").then((module) => module.PriceHistoryChart),
  { ssr: false },
);
type PriceRow = {
  id: string;
  observed_at: string;
  amount: string;
  provider: string;
  metric: string;
  deployment_id: string;
  source: string;
  source_url: string;
  unit: string;
};
export default function ModelDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [tab, setTab] = useState("Deployments");
  const { selected, toggle } = useCompare();
  const query = useQuery({
    queryKey: ["model", id],
    queryFn: () => api<ModelDetail>(`models/${id}`),
  });
  const pricing = useQuery({
    queryKey: ["prices", id],
    queryFn: () => api<PriceRow[]>(`models/${id}/pricing`),
    enabled: tab === "Price history",
  });
  const history = useQuery({
    queryKey: ["history", id],
    queryFn: () => api<MarketEvent[]>(`market-events?entity_id=${id}`),
    enabled: tab === "History",
  });
  if (query.isPending) return <Loading />;
  if (query.error)
    return <ErrorState error={query.error} retry={query.refetch} />;
  const data = query.data;
  if (!data) return null;
  const model = data.model;
  return (
    <>
      <Link className="source-link" href="/models" style={{ marginBottom: 22 }}>
        <ArrowLeft size={12} /> All models
      </Link>
      <div className="page-header">
        <div className="detail-heading">
          <span className="model-avatar">
            {(model.publisher ?? model.name).slice(0, 2).toUpperCase()}
          </span>
          <div>
            <div className="eyebrow">
              {model.publisher ?? "Publisher unresolved"} /{" "}
              {model.family ?? "Unclassified family"}
            </div>
            <h1>{model.name}</h1>
            <div className="detail-meta">
              <Badge
                tone={model.identity_status === "resolved" ? "good" : "warning"}
              >
                {model.identity_status} identity
              </Badge>
              <Badge>
                {model.open_weights == null
                  ? "Weights unknown"
                  : model.open_weights
                    ? "Open weights"
                    : "Closed weights"}
              </Badge>
              <span className="muted small">
                Released {date(model.release_date)}
              </span>
            </div>
          </div>
        </div>
        <button
          className="button"
          onClick={() => toggle({ id: model.id, name: model.name })}
        >
          <ArrowLeftRight size={13} />
          {selected.some((row) => row.id === id)
            ? "Remove from compare"
            : "Add to comparison"}
        </button>
      </div>
      {model.facts.description && (
        <p className="detail-description">
          {String(model.facts.description.value)}
        </p>
      )}
      <div className="stats-grid">
        {[
          { label: "Model context", value: tokens(model.context_window) },
          { label: "Provider listings", value: model.deployment_count },
          {
            label: "Tool calling",
            value: model.capabilities.includes("tool_calling")
              ? "Supported"
              : "Unknown",
          },
          { label: "Evidence", value: "Traceable" },
        ].map((stat) => (
          <div className="stat" key={stat.label}>
            <div className="stat-label">{stat.label}</div>
            <div className="stat-value" style={{ fontSize: 23 }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>
      <div className="tabs" role="tablist" aria-label="Model sections">
        {[
          "Deployments",
          "Capabilities",
          "Benchmarks",
          "Price history",
          "History",
          "Sources",
        ].map((name) => (
          <button
            role="tab"
            aria-selected={tab === name}
            key={name}
            className={tab === name ? "active" : ""}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </div>
      {tab === "Deployments" && (
        <>
          <div className="info-callout">
            <Info size={16} />
            <div>
              <strong>The same model. Different serving conditions.</strong>
              Context, exposed capabilities and prices belong to each
              deployment. Marketplace quotes do not bind an upstream provider.
            </div>
          </div>
          {data.deployments.length ? (
            <DeploymentTable deployments={data.deployments} />
          ) : (
            <Empty>No deployment observations are available.</Empty>
          )}
        </>
      )}
      {(tab === "Capabilities" || tab === "Sources") && (
        <div className="fact-grid">
          {Object.entries(model.facts).map(([key, fact]) => (
            <div className="fact-cell" key={key}>
              <label>{humanize(key)}</label>
              <EvidenceValue fact={fact} />
            </div>
          ))}
        </div>
      )}
      {tab === "Benchmarks" &&
        (data.benchmarks.length ? (
          <>
            <div className="info-callout">
              <Info size={16} />
              <div>
                <strong>Methodology matters</strong>Unspecified versions and
                scales are retained as evidence but excluded from normalized
                quality rankings.
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Benchmark</th>
                    <th>Raw score</th>
                    <th>Verification</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.benchmarks as Benchmark[]).map((row) => (
                    <tr key={row.id}>
                      <td>
                        {row.name}
                        <small className="muted" style={{ display: "block" }}>
                          {row.metric}
                        </small>
                      </td>
                      <td className="mono">
                        {row.score.replace(/(\.\d*?[1-9])0+$|\.0+$/, "$1")}
                      </td>
                      <td>
                        <Badge tone="warning">{row.verification}</Badge>
                      </td>
                      <td>
                        <SourceLink
                          source={
                            row.report_url ? "Original report" : row.source
                          }
                          url={row.report_url ?? row.source_url}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <Empty title="No benchmark evidence">
            No sourced benchmark results have been ingested for this model. No
            score is inferred.
          </Empty>
        ))}
      {tab === "Price history" &&
        (pricing.isPending ? (
          <Loading />
        ) : pricing.error ? (
          <ErrorState error={pricing.error} retry={pricing.refetch} />
        ) : pricing.data?.length ? (
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Recorded price observations</h2>
                <p>
                  First observation is a point. A history appears as source
                  prices change.
                </p>
              </div>
            </div>
            <PriceHistoryChart
              rows={pricing.data.filter((row) => row.unit === "tokens")}
            />
            <p className="chart-caption">
              Up to 12 deployment / metric / source series. All observation
              history remains in the API.
            </p>
          </section>
        ) : (
          <Empty>No price observations yet.</Empty>
        ))}
      {tab === "History" &&
        (history.isPending ? (
          <Loading />
        ) : history.error ? (
          <ErrorState error={history.error} retry={history.refetch} />
        ) : history.data?.length ? (
          <EventList events={history.data} full />
        ) : (
          <Empty>No recorded model changes.</Empty>
        ))}
      <Footnote />
    </>
  );
}
