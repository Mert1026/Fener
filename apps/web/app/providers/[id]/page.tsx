"use client";
import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Info } from "lucide-react";
import { api, type Provider, type Deployment } from "@/lib/api";
import { DeploymentTable } from "@/components/deployment-table";
import {
  Empty,
  ErrorState,
  Footnote,
  Loading,
  PageHeader,
} from "@/components/ui";
export default function ProviderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [offset, setOffset] = useState(0);
  const query = useQuery({
    queryKey: ["provider", id, offset],
    queryFn: () =>
      api<{ provider: Provider; deployments: Deployment[] }>(
        `providers/${encodeURIComponent(id)}?limit=200&offset=${offset}`,
      ),
  });
  if (query.isPending) return <Loading />;
  if (query.error)
    return <ErrorState error={query.error} retry={query.refetch} />;
  const data = query.data;
  if (!data) return null;
  return (
    <>
      <PageHeader
        eyebrow="Access provider"
        title={data.provider.name}
        description={`${data.provider.deployment_count.toLocaleString()} observed listings · Each deployment retains its own price, limits and evidence.`}
      />
      <div className="info-callout">
        <Info size={16} />
        <div>
          <strong>Privacy and regional guarantees require evidence</strong>No
          data retention, training, or zero-retention promise is inferred from
          this provider’s name.
        </div>
      </div>
      {data.deployments.length ? (
        <DeploymentTable deployments={data.deployments} />
      ) : (
        <Empty>No deployments are available.</Empty>
      )}
      <div className="section-row">
        <span className="muted small">
          {offset + 1}–{offset + data.deployments.length} of{" "}
          {data.provider.deployment_count.toLocaleString()} listings
        </span>
        <div className="pagination">
          <button
            className="button"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 200))}
          >
            Previous
          </button>
          <button
            className="button"
            disabled={
              offset + data.deployments.length >= data.provider.deployment_count
            }
            onClick={() => setOffset(offset + 200)}
          >
            Next
          </button>
        </div>
      </div>
      <Footnote />
    </>
  );
}
