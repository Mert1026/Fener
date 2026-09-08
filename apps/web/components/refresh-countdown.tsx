"use client";
import { useIsFetching, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

const PERIOD_MS = 60_000;

/**
 * The countdown is not decoration: when it reaches zero it invalidates the
 * workspace queries, so the number always means "until your data refreshes".
 */
export function RefreshCountdown() {
  const client = useQueryClient();
  const fetching = useIsFetching();
  const [remaining, setRemaining] = useState(PERIOD_MS);
  useEffect(() => {
    let startedAt = Date.now();
    const tick = window.setInterval(() => {
      const left = PERIOD_MS - (Date.now() - startedAt);
      if (left <= 0) {
        startedAt = Date.now();
        setRemaining(PERIOD_MS);
        void client.invalidateQueries();
      } else {
        setRemaining(left);
      }
    }, 1000);
    return () => window.clearInterval(tick);
  }, [client]);
  const seconds = Math.max(0, Math.ceil(remaining / 1000));
  const label = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  return (
    <span
      className="refresh-countdown mono"
      role="timer"
      aria-live="off"
      title="Workspace data refreshes automatically"
    >
      <RefreshCw size={11} className={fetching ? "spin" : undefined} />
      {fetching ? "SYNCING" : `NEXT SYNC ${label}`}
    </span>
  );
}
