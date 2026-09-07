"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { api, type ModelPage, type Provider } from "@/lib/api";
import { ModelTable } from "@/components/model-table";
import { SinceDigest } from "@/components/since-digest";
import {
  Empty,
  ErrorState,
  Footnote,
  Loading,
  PageHeader,
} from "@/components/ui";

function Explorer() {
  const searchParams = useSearchParams();
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  const [search, setSearch] = useState(q);
  const [provider, setProvider] = useState(searchParams.get("provider") ?? "");
  const [capability, setCapability] = useState(
    searchParams.get("capability") ?? "",
  );
  const [context, setContext] = useState(
    searchParams.get("min_context") ?? "0",
  );
  const [weights, setWeights] = useState(false);
  const [unresolved, setUnresolved] = useState(false);
  const [sort, setSort] = useState("released");
  const [page, setPage] = useState(0);
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(q);
      setPage(0);
    }, 250);
    return () => clearTimeout(timer);
  }, [q]);
  const params = new URLSearchParams({
    q: search,
    sort,
    limit: "50",
    offset: String(page * 50),
    min_context: context,
    include_unresolved: String(unresolved),
  });
  if (provider) params.set("provider", provider);
  if (capability) params.set("capability", capability);
  if (weights) params.set("open_weights", "true");
  const queryString = params.toString();
  useEffect(() => {
    window.history.replaceState(null, "", `/models?${queryString}`);
  }, [queryString]);
  const query = useQuery({
    queryKey: ["models", queryString],
    queryFn: () => api<ModelPage>(`models?${queryString}`),
    placeholderData: keepPreviousData,
  });
  const providers = useQuery({
    queryKey: ["providers"],
    queryFn: () => api<Provider[]>("providers"),
  });
  return (
    <>
      <PageHeader
        eyebrow="The catalog"
        title="Model explorer"
        description="A source-backed view of models, capabilities, and where you can run them."
        action={
          <span className="badge blue">
            {query.data?.total.toLocaleString() ?? "—"} MODELS
          </span>
        }
      />
      <SinceDigest scope="models" />
      <div className="filters">
        <div className="filter-search">
          <Search size={15} />
          <input
            aria-label="Search models"
            placeholder="Search models, families, publishers…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select
          aria-label="Filter by provider"
          value={provider}
          onChange={(e) => {
            setProvider(e.target.value);
            setPage(0);
          }}
        >
          <option value="">All providers</option>
          {providers.data
            ?.filter((p) => p.deployment_count > 0)
            .map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
        </select>
        <select
          aria-label="Required capability"
          value={capability}
          onChange={(e) => {
            setCapability(e.target.value);
            setPage(0);
          }}
        >
          <option value="">All capabilities</option>
          <option value="tool_calling">Tool calling</option>
          <option value="reasoning">Reasoning</option>
          <option value="image_input">Vision</option>
          <option value="structured_output">Structured output</option>
        </select>
        <select
          aria-label="Minimum context"
          value={context}
          onChange={(e) => {
            setContext(e.target.value);
            setPage(0);
          }}
        >
          <option value="0">Any context</option>
          <option value="32000">32K+</option>
          <option value="128000">128K+</option>
          <option value="1000000">1M+</option>
        </select>
        <select
          aria-label="Sort catalog"
          value={sort}
          onChange={(e) => {
            setSort(e.target.value);
            setPage(0);
          }}
        >
          <option value="released">Recently released</option>
          <option value="name">Name A–Z</option>
          <option value="context">Largest context</option>
        </select>
      </div>
      <div className="filters">
        <label>
          <input
            type="checkbox"
            checked={weights}
            onChange={(e) => {
              setWeights(e.target.checked);
              setPage(0);
            }}
          />
          Open weights only
        </label>
        <label style={{ marginLeft: 14 }}>
          <input
            type="checkbox"
            checked={unresolved}
            onChange={(e) => {
              setUnresolved(e.target.checked);
              setPage(0);
            }}
          />
          Include unresolved identities
        </label>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} retry={query.refetch} />
      ) : query.data?.items.length ? (
        <ModelTable models={query.data.items} />
      ) : (
        <Empty title="No models match these filters">
          Try broadening the search or including unresolved source identities.
        </Empty>
      )}
      <div className="table-footer">
        <span>
          Input and output “from” prices may come from different deployments.
          Sort headers apply to this page.
        </span>
        <div className="pagination">
          <span>
            Page {page + 1} of{" "}
            {Math.max(1, Math.ceil((query.data?.total ?? 0) / 50))}
          </span>
          <button
            className="button"
            aria-label="Previous page"
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            <ChevronLeft size={13} />
          </button>
          <button
            className="button"
            aria-label="Next page"
            disabled={(page + 1) * 50 >= (query.data?.total ?? 0)}
            onClick={() => setPage(page + 1)}
          >
            <ChevronRight size={13} />
          </button>
        </div>
      </div>
      <Footnote />
    </>
  );
}
export default function ModelsPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Explorer />
    </Suspense>
  );
}
