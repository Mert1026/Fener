import Link from "next/link";
import {
  ArrowDownRight,
  ArrowUpRight,
  ArrowRight,
  Sparkles,
  Minus,
  ExternalLink,
} from "lucide-react";
import type { MarketEvent } from "@/lib/api";
import { date, humanize } from "@/lib/format";
import { marketChange } from "@/lib/market";
import { SourceLink } from "./ui";

export function EventList({
  events,
  full = false,
}: {
  events: MarketEvent[];
  full?: boolean;
}) {
  return (
    <div className={full ? "market-cards" : "event-list"}>
      {events.map((event) => {
        const change = marketChange(event);
        const Icon =
          change.direction === "up"
            ? ArrowUpRight
            : change.direction === "down"
              ? ArrowDownRight
              : change.direction === "new"
                ? Sparkles
                : Minus;
        const href =
          event.model_id || event.entity_type === "model"
            ? `/models/${event.model_id ?? event.entity_id}`
            : null;
        const name = event.model_name ?? event.title;
        return (
          <article
            key={event.id}
            className={full ? `market-card ${change.tone}` : "event-item"}
          >
            <div
              className={full ? "market-card-top" : `event-icon ${change.tone}`}
            >
              {full ? (
                <>
                  <span className="market-symbol">
                    {name.slice(0, 2).toUpperCase()}
                  </span>
                  <div className="market-identity">
                    {href ? (
                      <Link href={href}>
                        <h3>{name}</h3>
                      </Link>
                    ) : (
                      <h3>{name}</h3>
                    )}
                    <p>
                      {event.provider
                        ? humanize(event.provider)
                        : "Model catalog"}
                    </p>
                  </div>
                  <span
                    className={`market-direction ${change.tone}`}
                    aria-label={change.direction}
                  >
                    <Icon size={22} />
                  </span>
                </>
              ) : (
                <Icon size={16} />
              )}
            </div>
            <div className={full ? "market-card-body" : undefined}>
              {!full &&
                (href ? (
                  <Link href={href}>
                    <h3>{name}</h3>
                  </Link>
                ) : (
                  <h3>{name}</h3>
                ))}
              <div className="market-metric">
                <span>{change.label}</span>
                {change.percentage && (
                  <strong className={`change-pill ${change.tone}`}>
                    {change.percentage}
                  </strong>
                )}
              </div>
              {event.old_value != null ? (
                <div className={full ? "market-values" : "event-values"}>
                  <span className="market-old">{change.oldLabel}</span>
                  <ArrowRight size={14} aria-label="changed to" />
                  <strong>{change.newLabel}</strong>
                </div>
              ) : (
                <p className={full ? "market-discovery" : undefined}>
                  {event.event_type === "new_model"
                    ? "Added to the catalog"
                    : event.event_type === "new_deployment"
                      ? "New serving option discovered"
                      : "Source metadata updated"}
                </p>
              )}
              {change.unit && <p className="market-unit">{change.unit}</p>}
            </div>
            <div className={full ? "market-card-footer" : "event-meta"}>
              <SourceLink source={event.source} url={event.source_url} />
              <time dateTime={event.detected_at} title={event.detected_at}>
                {date(event.detected_at)}
              </time>
              {full && href && (
                <Link href={href} aria-label={`Inspect ${name}`}>
                  <ExternalLink size={13} />
                </Link>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}
