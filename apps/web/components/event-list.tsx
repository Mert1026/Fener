import Link from "next/link";
import { ArrowDownRight, Boxes, RefreshCw } from "lucide-react";
import type { MarketEvent } from "@/lib/api";
import { date, factValue, humanize } from "@/lib/format";
import { SourceLink } from "./ui";
export function EventList({
  events,
  full = false,
}: {
  events: MarketEvent[];
  full?: boolean;
}) {
  return (
    <div className={full ? "timeline panel" : "event-list"}>
      {events.map((event) => (
        <article className="event-item" key={event.id}>
          <span className="event-icon">
            {event.event_type === "price_change" ? (
              <ArrowDownRight size={14} />
            ) : event.event_type === "new_model" ? (
              <Boxes size={13} />
            ) : (
              <RefreshCw size={12} />
            )}
          </span>
          <div>
            {event.model_id || event.entity_type === "model" ? (
              <Link href={`/models/${event.model_id ?? event.entity_id}`}>
                <h3>{event.title}</h3>
              </Link>
            ) : (
              <h3>{event.title}</h3>
            )}
            <p>
              {humanize(event.event_type)} <span>·</span> {event.importance}{" "}
              importance
            </p>
            {full && event.old_value != null && (
              <div className="timeline-values">
                <span>{factValue(event.old_value)}</span>→
                <span className="accent">{factValue(event.new_value)}</span>
              </div>
            )}
            <div className="event-meta">
              <SourceLink source={event.source} url={event.source_url} />
              <time title={event.detected_at} className="muted small">
                {date(event.detected_at)}
              </time>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
