"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { EyeOff } from "lucide-react";
import { api, type WatchlistState } from "@/lib/api";
import { Empty } from "@/components/ui";

export function WatchlistPanel() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => api<WatchlistState>("watchlist"),
    retry: false,
    staleTime: 30_000,
  });
  const remove = useMutation({
    mutationFn: (modelId: string) =>
      api(`watchlist/${encodeURIComponent(modelId)}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["watchlist"] }),
  });
  // Loading, locked workspace or disabled private API: the panel stays quiet.
  if (query.isPending || query.isError) return null;
  const items = query.data.items;
  return (
    <section className="panel" aria-label="Watchlist">
      <div className="panel-header">
        <div>
          <h2>Watching</h2>
          <p>Favourite models — Telegram pings you when their prices move</p>
        </div>
        <span className="badge">
          {query.data.telegram_configured ? "TELEGRAM ON" : "TELEGRAM OFF"}
        </span>
      </div>
      {items.length ? (
        <ul className="watchlist">
          {items.map((item) => (
            <li key={item.model_id}>
              <Link href={`/models/${item.model_id}`}>{item.model_name}</Link>
              <button
                className="button small"
                aria-label={`Stop watching ${item.model_name}`}
                onClick={() => remove.mutate(item.model_id)}
                disabled={remove.isPending}
              >
                <EyeOff size={12} /> Unwatch
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <Empty>
          Watch models with the star button on their page to follow their price
          changes.
        </Empty>
      )}
      {!query.data.telegram_configured && (
        <p className="muted small">
          Set FENER_TELEGRAM_BOT_TOKEN and FENER_TELEGRAM_CHAT_ID in your .env
          to receive price-change notifications for watched models.
        </p>
      )}
    </section>
  );
}
