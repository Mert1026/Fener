"use client";
import Link from "next/link";
import { useState } from "react";
import Decimal from "decimal.js";
import { useQuery } from "@tanstack/react-query";
import { Info } from "lucide-react";
import { api, type Benchmark } from "@/lib/api";
import { BenchmarkFrontier } from "@/components/benchmark-frontier";
import {
  Badge,
  Empty,
  ErrorState,
  Footnote,
  Loading,
  PageHeader,
  SourceLink,
} from "@/components/ui";
export default function BenchmarksPage() {
  const [offset, setOffset] = useState(0);
  const query = useQuery({
    queryKey: ["benchmarks", offset],
    queryFn: () => api<Benchmark[]>(`benchmarks?limit=100&offset=${offset}`),
  });
  return (
    <>
      <PageHeader
        eyebrow="Quality evidence"
        title="Benchmarks, with context."
        description="Original results, methodology boundaries and verification states. No single magical AI score."
      />
      <div className="info-callout">
        <Info size={17} />
        <div>
          <strong>Raw scores are not interchangeable</strong>A missing version,
          evaluator or scale makes a result unsuitable for cross-model
          normalization. LLM Stats’ authenticated benchmark integration needs a
          verified API contract and key.
        </div>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} retry={query.refetch} />
      ) : query.data?.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Benchmark / version</th>
                <th>Model</th>
                <th>Raw score</th>
                <th>Comparability</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {query.data.map((row) => (
                <tr key={row.id}>
                  <td>
                    {row.name}
                    <small className="muted" style={{ display: "block" }}>
                      {row.version}
                    </small>
                  </td>
                  <td>
                    <Link href={`/models/${row.model_id}`}>
                      {row.model_name}
                    </Link>
                  </td>
                  <td className="mono">{new Decimal(row.score).toString()}</td>
                  <td>
                    <Badge tone={row.comparable ? "good" : "warning"}>
                      {row.comparable
                        ? "Scale known"
                        : "Methodology incomplete"}
                    </Badge>
                  </td>
                  <td>
                    <SourceLink source={row.source} url={row.source_url} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty title="No benchmark observations yet">
          Configure a supported benchmark source. Missing results are never
          replaced with demo scores.
        </Empty>
      )}
      <div className="section-row">
        <span className="muted small">
          Showing observations {offset + 1}–{offset + (query.data?.length ?? 0)}
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
              !query.data || query.data.length < 100 || query.isFetching
            }
            onClick={() => setOffset(offset + 100)}
          >
            Next
          </button>
        </div>
      </div>
      <BenchmarkFrontier />
      <Footnote />
    </>
  );
}
