"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type MarketEvent } from "@/lib/api";
import { EventList } from "@/components/event-list";
import { Empty, ErrorState, Loading, PageHeader } from "@/components/ui";
export default function MarketPage() {
  const [type, setType] = useState("");
  const [limit, setLimit] = useState(50);
  const query = useQuery({
    queryKey: ["events", type, limit],
    queryFn: () =>
      api<MarketEvent[]>(
        `market-events?limit=${limit}${type ? `&event_type=${type}` : ""}`,
      ),
  });
  return (
    <>
      <PageHeader
        eyebrow="Change intelligence"
        title="The market is moving."
        description="Price moves, new serving options and capability changes. Every signal links to its source; formatting-only changes are excluded."
      />
      <div className="tabs">
        {[
          { name: "All signals", value: "" },
          { name: "New models", value: "new_model" },
          { name: "Price changes", value: "price_change" },
          { name: "Deployments", value: "new_deployment" },
          { name: "Capabilities", value: "capability_change" },
          { name: "Context", value: "context_change" },
        ].map((item) => (
          <button
            key={item.name}
            className={type === item.value ? "active" : ""}
            onClick={() => setType(item.value)}
          >
            {item.name}
          </button>
        ))}
      </div>
      <div className="market-legend">
        <span>
          <i className="legend-dot positive" />
          Lower prices / expanded capabilities
        </span>
        <span>
          <i className="legend-dot negative" />
          Higher prices / reduced capabilities
        </span>
        <span>Discovery dates are not release dates.</span>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} retry={query.refetch} />
      ) : query.data?.length ? (
        <>
          <EventList events={query.data} full />
          {limit < 200 && query.data.length >= limit && (
            <button
              className="button"
              style={{ marginTop: 20 }}
              onClick={() => setLimit(Math.min(200, limit + 50))}
            >
              Load more signals
            </button>
          )}
        </>
      ) : (
        <Empty title="No changes of this kind yet">
          Changes appear when successive source observations differ. Initial
          discovery is not a new release claim.
        </Empty>
      )}
    </>
  );
}
