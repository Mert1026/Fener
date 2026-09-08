"use client";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  Boxes,
  Compass,
  Database,
  Layers3,
  Radio,
} from "lucide-react";
import { api, type ModelPage, type Overview } from "@/lib/api";
import { ModelTable } from "@/components/model-table";
import { EventList } from "@/components/event-list";
import { SinceDigest } from "@/components/since-digest";
import { WatchlistPanel } from "@/components/watchlist-panel";
import {
  Empty,
  ErrorState,
  Footnote,
  Loading,
  PageHeader,
} from "@/components/ui";
const ContextCostChart = dynamic(
  () => import("@/components/chart").then((module) => module.ContextCostChart),
  { ssr: false, loading: () => <div className="chart skeleton" /> },
);
export default function OverviewPage() {
  const query = useQuery({
    queryKey: ["overview"],
    queryFn: () => api<Overview>("overview"),
  });
  const catalog = useQuery({
    queryKey: ["chart-models"],
    queryFn: () => api<ModelPage>("models?limit=100&sort=context"),
  });
  const data = query.data;
  return (
    <>
      <PageHeader
        eyebrow="Market intelligence"
        title="The model market, in focus."
        description="Explore the ecosystem. Understand the trade-offs. Follow the evidence."
        action={
          <Link className="button primary" href="/find">
            <Compass size={14} /> Find a model <ArrowUpRight size={13} />
          </Link>
        }
      />
      <SinceDigest scope="all" />
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} retry={query.refetch} />
      ) : (
        data && (
          <>
            <div className="stats-grid">
              {[
                {
                  label: "Canonical models",
                  value: data.models,
                  meta: `${data.unresolved_models.toLocaleString()} identities awaiting resolution`,
                  icon: Boxes,
                },
                {
                  label: "Provider listings",
                  value: data.deployments,
                  meta: "Direct and marketplace access",
                  icon: Layers3,
                },
                {
                  label: "Access providers",
                  value: data.providers,
                  meta: "A wider view of the ecosystem",
                  icon: Radio,
                },
                {
                  label: "Fact observations",
                  value: data.observations,
                  meta: "Traceable to original sources",
                  icon: Database,
                },
              ].map((stat) => (
                <div className="stat" key={stat.label}>
                  <div className="stat-label">
                    {stat.label}
                    <stat.icon size={14} />
                  </div>
                  <div className="stat-value mono">
                    {stat.value.toLocaleString()}
                  </div>
                  <div className="stat-meta">{stat.meta}</div>
                </div>
              ))}
            </div>
            <div className="dashboard-grid">
              <section className="panel span-all">
                <div className="panel-header">
                  <div>
                    <h2>Context meets cost</h2>
                    <p>
                      Serving price and model context. Quality is a separate
                      question.
                    </p>
                  </div>
                  <span className="badge">LIVE CATALOG</span>
                </div>
                {catalog.data?.items.length ? (
                  <ContextCostChart models={catalog.data.items} />
                ) : (
                  <Empty>
                    Run the first source sync to reveal the landscape.
                  </Empty>
                )}
                <div className="chart-caption">
                  <span className="evidence-dot" /> Up to 100 models · lowest
                  listed input rate · click a point to inspect
                </div>
              </section>
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Market signals</h2>
                    <p>The latest observed changes</p>
                  </div>
                  <Link href="/market">
                    View feed <ArrowUpRight size={12} />
                  </Link>
                </div>
                {data.recent_events.length ? (
                  <EventList events={data.recent_events.slice(0, 4)} />
                ) : (
                  <Empty>No market events have been observed.</Empty>
                )}
              </section>
              <WatchlistPanel />
            </div>
            <div className="section-row">
              <div>
                <h2>Recently released models</h2>
                <p>
                  Release dates reported by the catalog, with original evidence.
                </p>
              </div>
              <Link className="button" href="/models">
                Explore catalog <ArrowRight size={13} />
              </Link>
            </div>
            {data.recent_models.length ? (
              <ModelTable models={data.recent_models} compact />
            ) : (
              <Empty title="Your catalog is ready for its first sync">
                Run <code>uv run fener sync</code> to ingest real catalog data.
              </Empty>
            )}
            <div className="panel source-strip" style={{ marginTop: 22 }}>
              <span>CONNECTED INTELLIGENCE</span>
              {data.sources.map((source) => (
                <Link
                  key={source.id}
                  href="/data-health"
                  className={`source-status ${source.status !== "success" ? "pending" : ""}`}
                >
                  <span className="status-dot" />
                  {source.name}
                </Link>
              ))}
            </div>
            <Footnote />
          </>
        )
      )}
    </>
  );
}
