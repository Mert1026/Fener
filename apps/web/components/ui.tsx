"use client";
import { AlertCircle, ArrowUpRight, Database, RefreshCw } from "lucide-react";
import Link from "next/link";
import type { Evidence } from "@/lib/api";
import { date, factValue } from "@/lib/format";

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </header>
  );
}
export function Loading() {
  return (
    <div className="loading" role="status" aria-label="Loading data">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="skeleton" />
      ))}
      <span className="sr-only">Loading source-backed data…</span>
    </div>
  );
}
export function Empty({
  title = "No data yet",
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-beacon" aria-hidden />
      <Database size={28} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error;
  retry: () => unknown;
}) {
  return (
    <div className="error-state" role="alert">
      <AlertCircle />
      <div>
        <h3>Unable to load this view</h3>
        <p>{error.message}</p>
        <button className="button" onClick={() => retry()}>
          <RefreshCw size={14} /> Try again
        </button>
      </div>
    </div>
  );
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "good" | "warning" | "blue";
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function SourceLink({ source, url }: { source: string; url: string }) {
  const safe = url.startsWith("https://") || url.startsWith("http://");
  return safe ? (
    <a
      className="source-link"
      href={url}
      target="_blank"
      rel="noopener noreferrer"
    >
      {source.replaceAll("_", ".")}
      <ArrowUpRight size={11} />
    </a>
  ) : (
    <span>{source}</span>
  );
}
export function EvidenceValue({
  fact,
  children,
}: {
  fact?: Evidence;
  children?: React.ReactNode;
}) {
  if (!fact) return <span className="muted">Unknown</span>;
  return (
    <Link
      className="evidence evidence-link"
      href={`/evidence/${fact.id}`}
      title={`${fact.source} · ${fact.verification} · Last confirmed ${date(fact.last_seen_at)}${fact.stale ? " · Stale" : ""}. Inspect evidence.`}
    >
      {children ?? factValue(fact.value)}
      <span className={`evidence-dot ${fact.stale ? "stale" : ""}`} />
    </Link>
  );
}
export function Footnote() {
  return (
    <footer className="data-footnote">
      <span className="evidence-dot" /> Source-backed observations · Prices in
      USD / 1M tokens unless stated. Unknown values are never estimated.
    </footer>
  );
}
