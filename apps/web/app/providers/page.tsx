"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Search } from "lucide-react";
import { api, type Provider } from "@/lib/api";
import {
  Badge,
  Empty,
  ErrorState,
  Footnote,
  Loading,
  PageHeader,
} from "@/components/ui";
export default function ProvidersPage() {
  const [q, setQ] = useState("");
  const query = useQuery({
    queryKey: ["providers"],
    queryFn: () => api<Provider[]>("providers"),
  });
  const rows = query.data?.filter(
    (p) =>
      p.deployment_count > 0 &&
      `${p.name} ${p.id}`.toLowerCase().includes(q.toLowerCase()),
  );
  return (
    <>
      <PageHeader
        eyebrow="Inference access"
        title="Providers & platforms"
        description="Where models are served. Access platforms stay separate from underlying inference providers."
      />
      <div className="filters">
        <div className="filter-search">
          <Search size={15} />
          <input
            aria-label="Search providers"
            placeholder="Find a provider…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <span className="muted small">
          {rows?.length ?? 0} access providers
        </span>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} retry={query.refetch} />
      ) : rows?.length ? (
        <div className="provider-grid">
          {rows.map((provider) => (
            <Link
              className="panel provider-card"
              href={`/providers/${encodeURIComponent(provider.id)}`}
              key={provider.id}
            >
              <div className="provider-top">
                <span className="model-avatar">
                  {provider.name.slice(0, 2).toUpperCase()}
                </span>
                <ArrowUpRight size={15} className="muted" />
              </div>
              <h2>{provider.name}</h2>
              <p>
                {provider.deployment_count.toLocaleString()} catalog listings
              </p>
              <footer>
                <span>{provider.id}</span>
                <Badge
                  tone={provider.kind === "marketplace" ? "blue" : "neutral"}
                >
                  {provider.kind === "marketplace"
                    ? "Marketplace"
                    : "Access provider"}
                </Badge>
              </footer>
            </Link>
          ))}
        </div>
      ) : (
        <Empty>No providers match your search.</Empty>
      )}
      <Footnote />
    </>
  );
}
