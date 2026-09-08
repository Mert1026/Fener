"use client";
import { useIsFetching, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";

type SourceInfo = {
  id: string;
  last_success_at: string | null;
  interval_seconds: number;
};

/** Earliest moment any source is scheduled to produce new data. */
function nextUpdateAt(sources: SourceInfo[]): number | null {
  let min: number | null = null;
  for (const source of sources) {
    if (!source.last_success_at) continue;
    const due =
      Date.parse(source.last_success_at) + source.interval_seconds * 1000;
    if (Number.isFinite(due) && (min === null || due < min)) min = due;
  }
  return min;
}

function format(remainingMs: number): string {
  const total = Math.max(0, Math.ceil(remainingMs / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  const pad = (value: number) => String(value).padStart(2, "0");
  return hours > 0
    ? `${hours}:${pad(minutes)}:${pad(seconds)}`
    : `${minutes}:${pad(seconds)}`;
}

/**
 * The countdown means what it says: it derives the next data update from the
 * sources' real sync schedule (last success + interval) and refreshes the
 * workspace once when that moment arrives. The only recurring request is one
 * lightweight schedule poll per minute.
 */
export function RefreshCountdown() {
  const client = useQueryClient();
  const fetching = useIsFetching();
  const [now, setNow] = useState<number | null>(null);
  const invalidatedFor = useRef<number | null>(null);
  const schedule = useQuery({
    queryKey: ["source-schedule"],
    queryFn: () => api<SourceInfo[]>("sources"),
    refetchInterval: 60_000,
    staleTime: 55_000,
  });
  const dueAt = useMemo(
    () => nextUpdateAt(schedule.data ?? []),
    [schedule.data],
  );

  useEffect(() => {
    // First readout lands on the next task (hydration-safe), then ticks 1s.
    const start = window.setTimeout(() => setNow(Date.now()), 0);
    const tick = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      window.clearTimeout(start);
      window.clearInterval(tick);
    };
  }, []);

  // A source window elapsed: refresh exactly once for that moment.
  useEffect(() => {
    if (now === null || dueAt === null || now < dueAt) return;
    if (invalidatedFor.current === dueAt) return;
    invalidatedFor.current = dueAt;
    void client.invalidateQueries();
  }, [now, dueAt, client]);

  let label: string;
  if (now === null || schedule.isPending) {
    label = "NEXT SYNC --:--";
  } else if (dueAt === null) {
    label = "LIVE";
  } else if (now >= dueAt) {
    label = "SYNCING";
  } else {
    label = `NEXT SYNC ${format(dueAt - now)}`;
  }

  return (
    <span
      className="refresh-countdown mono"
      role="timer"
      aria-live="off"
      title="Counting down to the next source sync"
    >
      <RefreshCw
        size={11}
        className={
          fetching || (dueAt !== null && now !== null && now >= dueAt)
            ? "spin"
            : undefined
        }
      />
      {fetching ? "SYNCING" : label}
    </span>
  );
}
