"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQueries } from "@tanstack/react-query";
import Decimal from "decimal.js";
import { ArrowRight, Calculator, X } from "lucide-react";
import { api, type Deployment, type ModelDetail } from "@/lib/api";
import { useCompare } from "@/lib/compare-store";
import { SinceDigest } from "@/components/since-digest";
import { money, tokens } from "@/lib/format";
import {
  Badge,
  Empty,
  ErrorState,
  EvidenceValue,
  Footnote,
  Loading,
  PageHeader,
} from "@/components/ui";

function price(row: Deployment, metric: string): string | null {
  return (
    (row.facts[`price.${metric}`]?.value as { amount: string } | undefined)
      ?.amount ?? null
  );
}
function cheapest(rows: Deployment[]): Deployment | undefined {
  return [...rows].sort((a, b) =>
    new Decimal(price(a, "input_tokens") ?? "Infinity").comparedTo(
      new Decimal(price(b, "input_tokens") ?? "Infinity"),
    ),
  )[0];
}
export default function ComparePage() {
  const { selected, toggle } = useCompare();
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [usage, setUsage] = useState({
    requests: 10000,
    input_tokens: 2000,
    output_tokens: 500,
    cached_input_tokens: 0,
  });
  const queries = useQueries({
    queries: selected.map((item) => ({
      queryKey: ["model", item.id],
      queryFn: () => api<ModelDetail>(`models/${item.id}`),
    })),
  });
  const data = queries.flatMap((query) => (query.data ? [query.data] : []));
  const deployments = useMemo(
    () =>
      data.map(
        (row) =>
          row.deployments.find((d) => d.id === choices[row.model.id]) ??
          cheapest(row.deployments),
      ),
    [data, choices],
  );
  const cost = useMutation({
    mutationFn: async () =>
      Promise.all(
        deployments.map(async (deployment) =>
          deployment
            ? {
                name: deployment.model_name,
                ...(await api<{
                  estimated_cost: string | null;
                  missing: string[];
                  assumptions: string[];
                }>(`deployments/${deployment.id}/cost`, {
                  method: "POST",
                  body: JSON.stringify(usage),
                })),
              }
            : null,
        ),
      ),
  });
  return (
    <>
      <PageHeader
        eyebrow="Side by side"
        title="Compare the trade-offs"
        description="Compare up to six canonical models. Choose a specific deployment before estimating your workload."
        action={
          <Link className="button" href="/models">
            Add models <ArrowRight size={13} />
          </Link>
        }
      />
      <SinceDigest scope="models" />
      {selected.length < 2 ? (
        <Empty title="Start with two models">
          Select models in the{" "}
          <Link href="/models" className="accent">
            model explorer
          </Link>
          . Your comparison stays in this browser.
        </Empty>
      ) : queries.some((query) => query.isPending) ? (
        <Loading />
      ) : queries.some((query) => query.error) ? (
        <ErrorState
          error={queries.find((query) => query.error)!.error!}
          retry={() => queries.forEach((query) => query.refetch())}
        />
      ) : (
        <>
          <div className="compare-grid">
            {data.map((row, index) => {
              const deployment = deployments[index];
              return (
                <section className="panel compare-card" key={row.model.id}>
                  <div
                    style={{ display: "flex", justifyContent: "space-between" }}
                  >
                    <span className="model-avatar">
                      {(row.model.publisher ?? row.model.name)
                        .slice(0, 2)
                        .toUpperCase()}
                    </span>
                    <button
                      className="icon-button"
                      aria-label={`Remove ${row.model.name}`}
                      onClick={() =>
                        toggle({ id: row.model.id, name: row.model.name })
                      }
                    >
                      <X size={14} />
                    </button>
                  </div>
                  <Link href={`/models/${row.model.id}`}>
                    <h2>{row.model.name}</h2>
                  </Link>
                  <p className="small">
                    {row.model.publisher ?? "Publisher unknown"}
                  </p>
                  <select
                    aria-label={`Deployment for ${row.model.name}`}
                    value={deployment?.id ?? ""}
                    onChange={(e) => {
                      setChoices({
                        ...choices,
                        [row.model.id]: e.target.value,
                      });
                      cost.reset();
                    }}
                  >
                    {row.deployments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.access_provider} ·{" "}
                        {d.upstream_provider ?? "upstream unknown"} ·{" "}
                        {d.variant}
                      </option>
                    ))}
                  </select>
                  {deployment?.listing_kind === "routing_quote" && (
                    <Badge tone="warning">Unbound routing quote</Badge>
                  )}
                  {[
                    {
                      label: "Model context",
                      value: tokens(row.model.context_window),
                      fact: row.model.facts.context_window,
                    },
                    {
                      label: "Serving context",
                      fact: deployment?.facts.context_window,
                      value: tokens(
                        deployment?.facts.context_window?.value as
                          number | undefined,
                      ),
                    },
                    {
                      label: "Input / 1M",
                      fact: deployment?.facts["price.input_tokens"],
                      value: deployment
                        ? money(price(deployment, "input_tokens"))
                        : "Unknown",
                    },
                    {
                      label: "Output / 1M",
                      fact: deployment?.facts["price.output_tokens"],
                      value: deployment
                        ? money(price(deployment, "output_tokens"))
                        : "Unknown",
                    },
                    {
                      label: "Cached input / 1M",
                      fact: deployment?.facts["price.cached_input"],
                      value: deployment
                        ? money(price(deployment, "cached_input"))
                        : "Unknown",
                    },
                    {
                      label: "Open weights",
                      fact: row.model.facts.open_weights,
                      value:
                        row.model.open_weights == null
                          ? "Unknown"
                          : row.model.open_weights
                            ? "Yes"
                            : "No",
                    },
                  ].map((metric) => (
                    <div className="compare-row" key={metric.label}>
                      <label>{metric.label}</label>
                      <EvidenceValue fact={metric.fact}>
                        <span className="mono">{metric.value}</span>
                      </EvidenceValue>
                    </div>
                  ))}
                  {[
                    "tool_calling",
                    "reasoning",
                    "structured_output",
                    "image_input",
                  ].map((cap) => (
                    <div className="compare-row" key={cap}>
                      <label>{cap.replaceAll("_", " ")}</label>
                      <EvidenceValue fact={deployment?.facts[cap]} />
                    </div>
                  ))}
                </section>
              );
            })}
          </div>
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Your workload, estimated</h2>
                <p>
                  Cached tokens are part of total input. Estimates use the
                  selected deployment.
                </p>
              </div>
              <Calculator size={17} className="muted" />
            </div>
            <div className="cost-inputs">
              {[
                { key: "requests", label: "Requests / month" },
                { key: "input_tokens", label: "Input / request" },
                { key: "output_tokens", label: "Output / request" },
                { key: "cached_input_tokens", label: "Cached input / request" },
              ].map((field) => (
                <div className="field" key={field.key}>
                  <label htmlFor={field.key}>{field.label}</label>
                  <input
                    id={field.key}
                    type="number"
                    min="0"
                    value={usage[field.key as keyof typeof usage]}
                    onChange={(e) => {
                      setUsage({
                        ...usage,
                        [field.key]: Number(e.target.value),
                      });
                      cost.reset();
                    }}
                  />
                </div>
              ))}
              <button
                className="button primary"
                disabled={cost.isPending}
                onClick={() => cost.mutate()}
              >
                {cost.isPending ? "Calculating…" : "Calculate costs"}
              </button>
            </div>
            {cost.error && (
              <div className="panel-content">
                <ErrorState error={cost.error} retry={() => cost.mutate()} />
              </div>
            )}
            {cost.data && (
              <div className="cost-output">
                {cost.data.map(
                  (result, index) =>
                    result && (
                      <div key={index}>
                        <label className="muted small">{result.name}</label>
                        <div
                          className="stat-value mono"
                          style={{ fontSize: 24 }}
                        >
                          {money(result.estimated_cost)}{" "}
                          <small className="muted" style={{ fontSize: 11 }}>
                            / month
                          </small>
                        </div>
                        {result.missing.length > 0 && (
                          <p className="small">
                            Missing: {result.missing.join(", ")}
                          </p>
                        )}
                      </div>
                    ),
                )}
              </div>
            )}
            <p className="chart-caption">
              Flat listed rates. Taxes, purchase fees, unlisted charges and tier
              changes excluded.
            </p>
          </section>
        </>
      )}
      <Footnote />
    </>
  );
}
