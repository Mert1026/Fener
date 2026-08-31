"use client";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ArrowUpRight, LockKeyhole } from "lucide-react";
import { api, isPrivateLocked, type Source } from "@/lib/api";
import { date, humanize } from "@/lib/format";
import {
  Badge,
  ErrorState,
  Loading,
  PageHeader,
  SourceLink,
} from "@/components/ui";
type Health = {
  runs: {
    id: string;
    source_id: string;
    status: string;
    started_at: string;
    records_discovered: number;
    records_changed: number;
    error: string | null;
  }[];
  conflicts: {
    id: string;
    field: string;
    status: string;
    observation_a: string;
    observation_b: string;
    resolution: string | null;
  }[];
  unresolved_models: number;
  conflict_count: number;
};
export default function DataHealthPage() {
  const [queued, setQueued] = useState("");
  const sync = useMutation({
    mutationFn: (source_id: string) =>
      api<{ status: string }>("internal/sync", {
        method: "POST",
        body: JSON.stringify({ source_id }),
      }),
    onSuccess: (data) =>
      setQueued(
        `Source ${data.status}. The worker processes queued syncs; refresh this view after it completes.`,
      ),
  });
  const sources = useQuery({
    queryKey: ["sources"],
    queryFn: () => api<Source[]>("sources"),
  });
  const health = useQuery({
    queryKey: ["data-health"],
    queryFn: () => api<Health>("data-health"),
    retry: false,
  });
  return (
    <>
      <PageHeader
        eyebrow="Trust & provenance"
        title="Data health"
        description="Source freshness, ingestion outcomes and disagreements. Trust is inspectable."
      />
      {sources.isPending ? (
        <Loading />
      ) : sources.error ? (
        <ErrorState error={sources.error} retry={sources.refetch} />
      ) : (
        <div className="data-health-grid">
          {sources.data?.map((source) => (
            <section className="panel source-card" key={source.id}>
              <header>
                <h2>{source.name}</h2>
                <Badge tone={source.status === "success" ? "good" : "warning"}>
                  {humanize(source.status)}
                </Badge>
              </header>
              <p>
                Last successful sync{" "}
                <strong>{date(source.last_success_at)}</strong>
              </p>
              <p style={{ marginTop: 7 }}>{source.attribution}</p>
              <footer>
                <SourceLink source="Source catalog" url={source.url} />
                <SourceLink
                  source="Terms & attribution"
                  url={source.terms_url}
                />
                {health.data && (
                  <button
                    className="button"
                    disabled={sync.isPending}
                    onClick={() => sync.mutate(source.id)}
                  >
                    Queue sync
                  </button>
                )}
              </footer>
            </section>
          ))}
        </div>
      )}
      {queued && (
        <p role="status" className="info-callout">
          {queued}
        </p>
      )}
      {sync.error && (
        <p role="alert" className="error-state">
          {sync.error.message}
        </p>
      )}
      {health.isPending ? (
        <Loading />
      ) : health.error && !isPrivateLocked(health.error) ? (
        <ErrorState error={health.error} retry={health.refetch} />
      ) : health.error ? (
        <div className="info-callout">
          <LockKeyhole size={17} />
          <div>
            <strong>Detailed health is private</strong>Ingestion logs and
            conflict review require workspace authentication.
            <br />
            <Link className="button" style={{ marginTop: 12 }} href="/settings">
              Unlock workspace <ArrowUpRight size={12} />
            </Link>
          </div>
        </div>
      ) : (
        health.data && (
          <>
            <div className="section-row">
              <h2>Ingestion runs</h2>
              <span className="muted small">
                {health.data.unresolved_models.toLocaleString()} unresolved
                identities · {health.data.conflict_count.toLocaleString()}{" "}
                recorded conflicts
              </span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Started</th>
                    <th>Status</th>
                    <th>Discovered</th>
                    <th>Changed</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {health.data.runs.map((run) => (
                    <tr key={run.id}>
                      <td>{run.source_id}</td>
                      <td>{date(run.started_at)}</td>
                      <td>
                        <Badge
                          tone={run.status === "success" ? "good" : "warning"}
                        >
                          {run.status}
                        </Badge>
                      </td>
                      <td className="mono">{run.records_discovered}</td>
                      <td className="mono">{run.records_changed}</td>
                      <td>{run.error ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="section-row">
              <h2>Source disagreements</h2>
              <span className="muted small">
                First 100 records · Both observations are retained
              </span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Status</th>
                    <th>Evidence A</th>
                    <th>Evidence B</th>
                    <th>Resolution</th>
                  </tr>
                </thead>
                <tbody>
                  {health.data.conflicts.map((conflict) => (
                    <tr key={conflict.id}>
                      <td>{humanize(conflict.field)}</td>
                      <td>
                        <Badge>{humanize(conflict.status)}</Badge>
                      </td>
                      <td>
                        <Link
                          className="accent"
                          href={`/evidence/${conflict.observation_a}`}
                        >
                          Inspect →
                        </Link>
                      </td>
                      <td>
                        <Link
                          className="accent"
                          href={`/evidence/${conflict.observation_b}`}
                        >
                          Inspect →
                        </Link>
                      </td>
                      <td>{conflict.resolution ?? "Awaiting review"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )
      )}
    </>
  );
}
