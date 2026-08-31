"use client";
import { useState } from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { ArrowUpRight, Compass, ShieldCheck, Sparkles } from "lucide-react";
import { api, type Ranked, type Recommendation } from "@/lib/api";
import { money } from "@/lib/format";
import { Badge, Empty, ErrorState, PageHeader } from "@/components/ui";

function Result({ row, best = false }: { row: Ranked; best?: boolean }) {
  return (
    <article className={`panel result-card ${best ? "best" : ""}`}>
      <Badge tone={best ? "blue" : "neutral"}>
        {best ? "RECOMMENDED CANDIDATE" : "ALTERNATIVE"}
      </Badge>
      <Link href={`/models/${row.deployment.model_id}`}>
        <h2>{row.deployment.model_name}</h2>
      </Link>
      <p>
        {row.deployment.access_provider} →{" "}
        {row.deployment.upstream_provider ?? "Upstream unspecified"} ·{" "}
        <span className="mono">{row.deployment.api_model_id}</span>
      </p>
      <div className="result-metrics">
        <div>
          <label>ESTIMATED / MONTH</label>
          <strong>{money(row.estimated_cost)}</strong>
        </div>
        <div>
          <label>WEIGHT COVERAGE</label>
          <strong>{Math.round(Number(row.coverage) * 100)}%</strong>
        </div>
        <div>
          <label>CONFIDENCE</label>
          <Badge tone="warning">{row.confidence}</Badge>
        </div>
      </div>
      <p>{row.reason}</p>
      {row.missing_evidence.length > 0 && (
        <p style={{ marginTop: 7 }}>
          Missing evidence: {row.missing_evidence.join(", ")}
        </p>
      )}
      <ul>
        {row.assumptions.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </article>
  );
}
export default function FindPage() {
  const [task, setTask] = useState("General assistant");
  const [context, setContext] = useState(32000);
  const [tools, setTools] = useState(true);
  const [vision, setVision] = useState(false);
  const [open, setOpen] = useState(false);
  const [routing, setRouting] = useState(false);
  const [zeroRates, setZeroRates] = useState(false);
  const [unresolved, setUnresolved] = useState(false);
  const [budget, setBudget] = useState(100);
  const [latency, setLatency] = useState(0);
  const [usage, setUsage] = useState({
    requests: 10000,
    input_tokens: 2000,
    output_tokens: 500,
    cached_input_tokens: 0,
  });
  const result = useMutation({
    mutationFn: () =>
      api<Recommendation>("recommendations/preview", {
        method: "POST",
        body: JSON.stringify({
          task,
          required_capabilities: [
            ...(tools ? ["tool_calling"] : []),
            ...(vision ? ["image_input"] : []),
          ],
          min_context: context,
          open_weights: open,
          budget: String(budget),
          allow_routing_quotes: routing,
          allow_zero_metered_rates: zeroRates,
          allow_unresolved_models: unresolved,
          workload: usage,
          weights: { price: String(100 - latency), latency: String(latency) },
          limit: 6,
        }),
      }),
  });
  return (
    <>
      <PageHeader
        eyebrow="Deterministic intelligence"
        title="Find the right model for your work."
        description="Set the constraints. Compare real serving costs. See exactly why each candidate qualifies."
        action={
          <span className="private-badge">
            <ShieldCheck size={13} /> No inference calls
          </span>
        }
      />
      <div className="find-layout">
        <form
          className="panel"
          onSubmit={(e) => {
            e.preventDefault();
            result.mutate();
          }}
        >
          <div className="form-section">
            <h2>
              01 <span className="muted">/</span> Define the workload
            </h2>
            <div className="field">
              <label htmlFor="task">Workload label</label>
              <select
                id="task"
                value={task}
                onChange={(e) => setTask(e.target.value)}
              >
                {[
                  "General assistant",
                  "Coding agent",
                  "Research agent",
                  "Reviewer",
                  "Fast router",
                ].map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
              <small>
                Label only; capability and evidence weights determine ranking.
              </small>
            </div>
            <div className="form-grid" style={{ marginTop: 17 }}>
              {[
                { key: "requests", label: "Requests / month" },
                { key: "input_tokens", label: "Input tokens / request" },
                { key: "output_tokens", label: "Output tokens / request" },
                { key: "cached_input_tokens", label: "Cached input / request" },
              ].map((field) => (
                <div className="field" key={field.key}>
                  <label htmlFor={field.key}>{field.label}</label>
                  <input
                    id={field.key}
                    type="number"
                    min="0"
                    required
                    value={usage[field.key as keyof typeof usage]}
                    onChange={(e) =>
                      setUsage({
                        ...usage,
                        [field.key]: Number(e.target.value),
                      })
                    }
                  />
                </div>
              ))}
            </div>
          </div>
          <div className="form-section">
            <h2>
              02 <span className="muted">/</span> Set hard requirements
            </h2>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="context">Minimum context</label>
                <input
                  id="context"
                  type="number"
                  min="0"
                  value={context}
                  onChange={(e) => setContext(Number(e.target.value))}
                />
              </div>
              <div className="field">
                <label htmlFor="budget">Monthly budget · USD</label>
                <input
                  id="budget"
                  type="number"
                  min="0"
                  value={budget}
                  onChange={(e) => setBudget(Number(e.target.value))}
                />
              </div>
            </div>
            {[
              { label: "Confirmed tool calling", value: tools, set: setTools },
              { label: "Image understanding", value: vision, set: setVision },
              { label: "Open weights only", value: open, set: setOpen },
              {
                label: "Include zero metered rates (fees or quotas may apply)",
                value: zeroRates,
                set: setZeroRates,
              },
              {
                label: "Include unresolved model identities",
                value: unresolved,
                set: setUnresolved,
              },
              {
                label: "Allow marketplace routing quotes",
                value: routing,
                set: setRouting,
              },
            ].map((field) => (
              <label className="check-field" key={field.label}>
                <input
                  type="checkbox"
                  checked={field.value}
                  onChange={(e) => field.set(e.target.checked)}
                />
                {field.label}
              </label>
            ))}
          </div>
          <div className="form-section">
            <h2>
              03 <span className="muted">/</span> Choose evidence weights
            </h2>
            <div className="field">
              <label htmlFor="latency">
                Price {100 - latency}% · Latency {latency}%
              </label>
              <input
                id="latency"
                type="range"
                min="0"
                max="100"
                step="10"
                value={latency}
                onChange={(e) => setLatency(Number(e.target.value))}
              />
              <small>
                Missing latency lowers coverage. Unversioned benchmark scores
                are excluded.
              </small>
            </div>
            <button
              className="button primary"
              style={{ width: "100%", marginTop: 20 }}
              disabled={result.isPending}
            >
              <Compass size={15} />
              {result.isPending
                ? "Checking constraints…"
                : "Find matching deployments"}
              <ArrowUpRight size={13} />
            </button>
          </div>
        </form>
        <div>
          {result.isPending ? (
            <div className="panel result-card">
              <div className="skeleton" />
              <p style={{ marginTop: 16 }}>
                Checking capabilities, evidence freshness and your workload
                cost…
              </p>
            </div>
          ) : result.error ? (
            <ErrorState error={result.error} retry={() => result.mutate()} />
          ) : result.data ? (
            <>
              <div className="section-row" style={{ marginTop: 0 }}>
                <h2>Your candidate set</h2>
                <span className="muted small">
                  {result.data.eligible_count} eligible ·{" "}
                  {result.data.rejected_count} excluded
                </span>
              </div>
              {result.data.recommended ? (
                <Result row={result.data.recommended} best />
              ) : (
                <Empty title="No supported recommendation">
                  No deployment has both confirmed requirements and sufficient
                  requested evidence. Broaden constraints or ingest missing
                  data.
                </Empty>
              )}
              {result.data.alternatives.map((row) => (
                <Result key={row.deployment.id} row={row} />
              ))}
              {result.data.fallback_chain.length > 0 && (
                <section className="panel result-card">
                  <h3>Fallback chain</h3>
                  <p style={{ marginTop: 9 }}>
                    {result.data.fallback_chain
                      .map(
                        (row) =>
                          `${row.deployment.model_name} via ${row.deployment.access_provider}`,
                      )
                      .join(" → ")}
                  </p>
                </section>
              )}
              <details className="panel result-card">
                <summary>Why other candidates were excluded</summary>
                <ul>
                  {result.data.rejected.slice(0, 20).map((row) => (
                    <li key={row.deployment_id}>
                      <strong>{row.model_name}</strong>:{" "}
                      {row.reasons.join("; ")}
                    </li>
                  ))}
                </ul>
              </details>
            </>
          ) : (
            <>
              <div className="panel result-card">
                <Compass size={28} className="accent" />
                <h2>A decision you can inspect.</h2>
                <p>
                  Every recommendation starts with confirmed requirements and
                  sourced prices. Missing evidence stays visible.
                </p>
                <div className="compare-row" style={{ marginTop: 24 }}>
                  <span>1. Filter incompatible deployments</span>
                  <ShieldCheck size={14} className="muted" />
                </div>
                <div className="compare-row">
                  <span>2. Calculate your expected spend</span>
                  <span className="mono muted">Decimal</span>
                </div>
                <div className="compare-row">
                  <span>3. Rank with explicit evidence weights</span>
                  <span className="mono muted">0 AI calls</span>
                </div>
              </div>
              <div className="info-callout">
                <Sparkles size={16} />
                <div>
                  <strong>No invented quality scores</strong>Price-only results
                  have low confidence about task quality. Use verified benchmark
                  versions or your own evaluations before changing a production
                  policy.
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
