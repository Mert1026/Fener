"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Decimal from "decimal.js";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Info, Search, RefreshCw } from "lucide-react";
import { api, isPrivateLocked, type Benchmark } from "@/lib/api";
import { date } from "@/lib/format";
import { requestId } from "@/lib/uuid";
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
  version: string;
  evaluator: string;
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
    item_status_counts?: Record<string, number>;
    models_without_results?: number;
    failure_reasons?: { message: string; count: number }[];
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
          request_id: requestId(),
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
  const finishedWithoutResults =
    refresh.data?.refresh?.processed_models ===
      refresh.data?.refresh?.total_models &&
    refresh.data?.refresh?.imported_results === 0;
  return (
    <>
      <PageHeader
        eyebrow="Benchmark intelligence"
        title="Comparable model benchmarks."
        description="Fener reads the current Artificial Analysis Intelligence Index cohort directly. Only exact source-published model scores enter the comparison."
      />
      <section className="panel settings-panel" style={{ marginBottom: 20 }}>
        <div className="panel-header">
          <div>
            <h2>Catalog-wide benchmark update</h2>
            <p>
              One click reads Artificial Analysis&apos;s current public model
              dataset once and matches it against every resolved catalog model.
              Models outside that exact index version stay marked as no
              evidence. This benchmark update does not spend Z.ai tokens.
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
              {update.isPending
                ? "Queueing…"
                : refresh.data?.refresh?.status === "paused"
                  ? "Resume benchmarks"
                  : "Update all benchmarks"}
            </button>
          )}
        </div>
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
            {refresh.data.refresh.processed_models ===
              refresh.data.refresh.total_models && (
              <div className="small muted">
                <p>
                  {refresh.data.refresh.item_status_counts?.failed ?? 0}{" "}
                  rejected by validation ·{" "}
                  {refresh.data.refresh.item_status_counts?.uncertain ?? 0}{" "}
                  timed out or interrupted ·{" "}
                  {refresh.data.refresh.models_without_results ?? 0} completed
                  with no usable claim
                </p>
                {!!refresh.data.refresh.failure_reasons?.length && (
                  <details>
                    <summary>Why models produced no results</summary>
                    {(refresh.data.refresh.failure_reasons ?? []).map(
                      (reason) => (
                        <p key={reason.message}>
                          {reason.count} models: {reason.message}
                        </p>
                      ),
                    )}
                  </details>
                )}
              </div>
            )}
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
          <strong>Direct source data still requires review</strong>Fener accepts
          one exact Artificial Analysis index version, evaluator and metric.
          Coding-agent results stay separate because their harness and execution
          settings materially affect the score. Source-linked claims remain out
          of recommendations pending a review workflow.
        </div>
      </div>
      {groups.isPending ? (
        <Loading />
      ) : groups.error ? (
        <ErrorState error={groups.error} retry={groups.refetch} />
      ) : !groups.data?.length ? (
        <Empty
          title={
            finishedWithoutResults
              ? "Update finished with no usable benchmark claims"
              : "No benchmark evidence yet"
          }
        >
          {finishedWithoutResults
            ? "Nothing is hidden: no result passed the source and identity checks. Review the run diagnostics above before trying the direct source again."
            : "Press Update all benchmarks to compare every resolved catalog model with the current Artificial Analysis cohort."}
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
                  <span>
                    {group.version} · {group.metric}
                  </span>
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
                      {selected.version} · {selected.evaluator} ·{" "}
                      {selected.models} models
                    </p>
                  </div>
                  <Badge tone="warning">Source-extracted · unverified</Badge>
                </div>
                <p className="benchmark-note">
                  Alphabetical, not a leaderboard. Only the current comparable
                  source cohort is shown. Open the original report before
                  relying on a score.
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
                                  ? "Same benchmark cohort"
                                  : "Methodology incomplete"}
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
                                <p>Tested source variant: {row.source_title}</p>
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
