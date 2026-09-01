"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Decimal from "decimal.js";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Info, Search, RefreshCw } from "lucide-react";
import { api, isPrivateLocked, type Benchmark } from "@/lib/api";
import { date } from "@/lib/format";
import {
  Badge,
  Empty,
  ErrorState,
  Footnote,
  Loading,
  PageHeader,
  SourceLink,
} from "@/components/ui";

type Group = {
  id: string;
  name: string;
  metric: string;
  results: number;
  models: number;
  comparable_results: number;
};
type RefreshState = {
  configured: boolean;
  model: string;
  refresh: null | {
    id: string;
    status: string;
    total_models: number;
    processed_models: number;
    imported_results: number;
    failed_models: number;
    current_model: string | null;
    error: string | null;
  };
};
export default function BenchmarksPage() {
  const client = useQueryClient();
  const [chosen, setChosen] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const groups = useQuery({
    queryKey: ["benchmark-groups"],
    queryFn: () => api<Group[]>("benchmarks/groups"),
  });
  const refresh = useQuery({
    queryKey: ["benchmark-refresh"],
    queryFn: () => api<RefreshState>("benchmark-refresh"),
    retry: false,
    refetchInterval: (query) =>
      ["queued", "running", "blocked"].includes(
        query.state.data?.refresh?.status ?? "",
      )
        ? 5000
        : false,
  });
  const update = useMutation({
    mutationFn: () =>
      api<RefreshState>("benchmark-refresh", {
        method: "POST",
        body: JSON.stringify({
          request_id: crypto.randomUUID(),
          acknowledge_cost: true,
        }),
      }),
    onSuccess: (data) => client.setQueryData(["benchmark-refresh"], data),
  });
  useEffect(() => {
    if (refresh.data?.refresh?.processed_models) {
      client.invalidateQueries({ queryKey: ["benchmark-groups"] });
      client.invalidateQueries({ queryKey: ["benchmarks"] });
    }
  }, [client, refresh.data?.refresh?.processed_models]);
  const choices = (groups.data ?? []).filter((g) =>
    `${g.name} ${g.metric}`.toLowerCase().includes(search.toLowerCase()),
  );
  const selected = choices.find((g) => g.id === chosen) ?? choices[0];
  const query = useQuery({
    queryKey: ["benchmarks", selected?.id, offset],
    queryFn: () =>
      api<Benchmark[]>(
        `benchmarks?limit=100&offset=${offset}&group_id=${selected!.id}`,
      ),
    enabled: !!selected,
  });
  return (
    <>
      <PageHeader
        eyebrow="Benchmark intelligence"
        title="Research benchmarks for the whole catalog."
        description="Update runs AI research across every resolved catalog model and adds complete cited benchmark claims. Every result stays unverified until you inspect its original report."
      />
      <section className="panel settings-panel" style={{ marginBottom: 20 }}>
        <div className="panel-header">
          <div>
            <h2>Catalog-wide benchmark update</h2>
            <p>
              One click queues every resolved model. Each model can use one web
              search and one summary request, so a full update may take hours
              and incur substantial API charges. Failed or interrupted items are
              not retried automatically.
            </p>
          </div>
          {isPrivateLocked(refresh.error) ? (
            <Link className="button" href="/settings">
              Unlock to update
            </Link>
          ) : (
            <button
              className="button primary"
              disabled={
                update.isPending ||
                !refresh.data?.configured ||
                ["queued", "running", "blocked"].includes(
                  refresh.data?.refresh?.status ?? "",
                )
              }
              onClick={() => update.mutate()}
            >
              <RefreshCw size={14} />
              {update.isPending ? "Queueing…" : "Update all benchmarks"}
            </button>
          )}
        </div>
        {refresh.data && !refresh.data.configured && (
          <p className="error-state">
            Configure ZAI_API_KEY and restart Fener.
          </p>
        )}
        {refresh.data?.refresh && (
          <div className="stack" style={{ marginTop: 15 }}>
            <progress
              max={refresh.data.refresh.total_models}
              value={refresh.data.refresh.processed_models}
              style={{ width: "100%" }}
            />
            <p className="small">
              {refresh.data.refresh.processed_models} /{" "}
              {refresh.data.refresh.total_models} models ·{" "}
              {refresh.data.refresh.imported_results} cited results ·{" "}
              {refresh.data.refresh.failed_models} failed or uncertain · Status:{" "}
              {refresh.data.refresh.status.replaceAll("_", " ")}
              {refresh.data.refresh.current_model
                ? ` · Researching ${refresh.data.refresh.current_model}`
                : ""}
            </p>
            {refresh.data.refresh.error && (
              <p className="error-state">{refresh.data.refresh.error}</p>
            )}
          </div>
        )}
        {update.error && (
          <ErrorState error={update.error} retry={() => update.mutate()} />
        )}
      </section>
      <div className="info-callout">
        <Info size={18} />
        <div>
          <strong>AI extraction is not verification</strong>The update must cite
          an approved source and provide an exact model, metric, score, version
          and evaluator. Fener keeps these claims out of rankings and
          recommendations until a future human-review workflow exists.
        </div>
      </div>
      {groups.isPending ? (
        <Loading />
      ) : groups.error ? (
        <ErrorState error={groups.error} retry={groups.refetch} />
      ) : !groups.data?.length ? (
        <Empty title="No benchmark evidence yet">
          Press Update all benchmarks to research every resolved catalog model.
          Catalog source syncs never fill this page.
        </Empty>
      ) : (
        <div className="benchmark-layout">
          <aside
            className="panel benchmark-picker"
            aria-label="Benchmark groups"
          >
            <label className="benchmark-search">
              <Search size={14} />
              <input
                aria-label="Search benchmark groups"
                placeholder="Find a benchmark…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setOffset(0);
                }}
              />
            </label>
            <p className="small muted">{choices.length} metric groups</p>
            <div className="benchmark-group-list">
              {choices.map((group) => (
                <button
                  key={group.id}
                  className={`benchmark-group ${selected?.id === group.id ? "active" : ""}`}
                  aria-pressed={selected?.id === group.id}
                  onClick={() => {
                    setChosen(group.id);
                    setOffset(0);
                  }}
                >
                  <strong>{group.name}</strong>
                  <span>{group.metric}</span>
                  <small>
                    {group.models} models · {group.results} results
                  </small>
                </button>
              ))}
            </div>
          </aside>
          <section className="panel benchmark-results">
            {!selected ? (
              <Empty>No groups match that search.</Empty>
            ) : (
              <>
                <div className="panel-header">
                  <div>
                    <h2>{selected.name}</h2>
                    <p>
                      Reported metric:{" "}
                      <strong className="accent">{selected.metric}</strong> ·{" "}
                      {selected.models} models
                    </p>
                  </div>
                  <Badge tone="warning">AI-researched · unverified</Badge>
                </div>
                <p className="benchmark-note">
                  Alphabetical, not a leaderboard. Only cited AI research is
                  shown. Open the original report before relying on a score.
                </p>
                {query.isPending ? (
                  <Loading />
                ) : query.error ? (
                  <ErrorState error={query.error} retry={query.refetch} />
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Model</th>
                          <th>Reported score</th>
                          <th>Methodology</th>
                          <th>Original report</th>
                        </tr>
                      </thead>
                      <tbody>
                        {query.data?.map((row) => (
                          <tr key={row.id}>
                            <td>
                              <Link href={`/models/${row.model_id}`}>
                                {row.model_name}
                              </Link>
                            </td>
                            <td>
                              <strong className="benchmark-score mono">
                                {new Decimal(row.score).toString()}
                              </strong>
                              <small className="benchmark-unit">
                                {row.metric}
                              </small>
                            </td>
                            <td>
                              <Badge tone={row.comparable ? "good" : "warning"}>
                                {row.comparable
                                  ? "Comparable evidence"
                                  : "Needs verification"}
                              </Badge>
                              <details className="benchmark-issues">
                                <summary>
                                  {row.quality_issues.length
                                    ? `${row.quality_issues.length} evidence gaps`
                                    : "Methodology"}
                                </summary>
                                {row.quality_issues.map((issue) => (
                                  <p key={issue}>{issue}</p>
                                ))}
                                <p>
                                  Version:{" "}
                                  {row.version.startsWith("unspecified:")
                                    ? "Not supplied"
                                    : row.version}
                                </p>
                                <p>Evaluator: {row.evaluator}</p>
                              </details>
                            </td>
                            <td>
                              {row.report_url ? (
                                <SourceLink
                                  source="View report"
                                  url={row.report_url}
                                />
                              ) : (
                                <span className="muted">
                                  Report not identified
                                </span>
                              )}
                              <small className="benchmark-unit">
                                {row.reported_date
                                  ? `Reported ${date(row.reported_date)}`
                                  : "Report date unknown"}
                              </small>
                              {row.source_url !== row.report_url && (
                                <SourceLink
                                  source={`Via ${row.source}`}
                                  url={row.source_url}
                                />
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <div className="benchmark-pagination">
                  <span className="muted small">
                    {query.data?.length ?? 0} results on this page
                  </span>
                  <div className="pagination">
                    <button
                      className="button"
                      disabled={offset === 0 || query.isFetching}
                      onClick={() => setOffset(Math.max(0, offset - 100))}
                    >
                      Previous
                    </button>
                    <button
                      className="button"
                      disabled={
                        (query.data?.length ?? 0) < 100 || query.isFetching
                      }
                      onClick={() => setOffset(offset + 100)}
                    >
                      Next
                    </button>
                  </div>
                </div>
              </>
            )}
          </section>
        </div>
      )}
      <Footnote />
    </>
  );
}
