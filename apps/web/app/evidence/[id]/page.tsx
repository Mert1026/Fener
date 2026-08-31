"use client";
import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { date } from "@/lib/format";
import {
  Badge,
  ErrorState,
  Loading,
  PageHeader,
  SourceLink,
} from "@/components/ui";
type Record = {
  field: string;
  normalized_value: unknown;
  raw_record: unknown;
  source: string;
  source_url: string;
  snapshot_id: string;
  observed_at: string;
  last_seen_at: string;
  verification: string;
};
export default function EvidencePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const query = useQuery({
    queryKey: ["evidence", id],
    queryFn: () => api<Record>(`observations/${id}`),
  });
  if (query.isPending) return <Loading />;
  if (query.error)
    return <ErrorState error={query.error} retry={query.refetch} />;
  const data = query.data;
  if (!data) return null;
  return (
    <>
      <PageHeader
        eyebrow="The evidence trail"
        title="Where this value came from"
        description={`Observed ${date(data.observed_at)} · Last seen ${date(data.last_seen_at)}`}
        action={<Badge tone="blue">{data.verification}</Badge>}
      />
      <div className="stack">
        <section className="panel settings-panel">
          <h2>{data.field}</h2>
          <pre className="code-block">
            {JSON.stringify(data.normalized_value, null, 2)}
          </pre>
          <div style={{ marginTop: 15 }}>
            <SourceLink source={data.source} url={data.source_url} />
          </div>
        </section>
        <section className="panel settings-panel">
          <h2>Original source record</h2>
          <p>
            Snapshot reference: <span className="mono">{data.snapshot_id}</span>
            . The content-addressed original response is retained in local
            snapshot storage.
          </p>
          <pre className="code-block">
            {JSON.stringify(data.raw_record, null, 2)}
          </pre>
        </section>
      </div>
    </>
  );
}
