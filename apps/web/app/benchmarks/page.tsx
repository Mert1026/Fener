"use client";
import Link from "next/link";
import { useState } from "react";
import Decimal from "decimal.js";
import { useQuery } from "@tanstack/react-query";
import { Info, ArrowUpRight, Search } from "lucide-react";
import { api, type Benchmark } from "@/lib/api";
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
export default function BenchmarksPage() {
  const [chosen, setChosen] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const groups = useQuery({
    queryKey: ["benchmark-groups"],
    queryFn: () => api<Group[]>("benchmarks/groups"),
  });
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
        eyebrow="Benchmark evidence"
        title="Compare the same measurement."
        description="Elo, accuracy and win rate measure different things. Results are separated by their reported metric, with original reports attached."
        action={
          <Link className="button" href="/research">
            Investigate a result <ArrowUpRight size={13} />
          </Link>
        }
      />
      <div className="info-callout">
        <Info size={18} />
        <div>
          <strong>Same name does not mean the same scale</strong>For example,
          GDPval-AA includes both Elo ratings and win-rate reports. They now
          have separate groups. No guessed conversions, blended scores or
          rankings across incompatible tests.
        </div>
      </div>
      {groups.isPending ? (
        <Loading />
      ) : groups.error ? (
        <ErrorState error={groups.error} retry={groups.refetch} />
      ) : !groups.data?.length ? (
        <Empty title="No benchmark evidence yet">
          Results will appear after a supported source sync.
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
                  <Badge tone="warning">Source-reported</Badge>
                </div>
                <p className="benchmark-note">
                  Alphabetical, not a leaderboard. Latest observation per model,
                  definition, evaluator and metric. Version and test settings
                  must also match before results can be ranked.
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
                              <SourceLink
                                source={`Via ${row.source}`}
                                url={row.source_url}
                              />
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
