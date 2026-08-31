"use client";
import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ScanSearch,
  ShieldCheck,
  ExternalLink,
  RefreshCw,
  Info,
} from "lucide-react";
import { api, isPrivateLocked } from "@/lib/api";
import { date, humanize } from "@/lib/format";
import { PrivateGate } from "@/components/private-gate";
import { Badge, Empty, ErrorState, Loading, PageHeader } from "@/components/ui";

type Run = {
  id: string;
  query: string;
  model: string;
  status: string;
  created_at: string;
  error: string | null;
  report: null | {
    blocks: { text: string; url?: string; title?: string }[][];
    sources: { url: string; title: string }[];
    usage: { input_tokens?: number; output_tokens?: number };
  };
};
type Research = {
  configured: boolean;
  model: string;
  daily_limit: number;
  domains: string[];
  runs: Run[];
};
export default function ResearchPage() {
  const client = useQueryClient();
  const [question, setQuestion] = useState("");
  const [approved, setApproved] = useState(false);
  const query = useQuery({
    queryKey: ["research"],
    queryFn: () => api<Research>("research"),
    retry: false,
    refetchInterval: (q) =>
      q.state.data?.runs.some((r) => r.status === "running") ? 5000 : false,
  });
  const create = useMutation({
    mutationFn: () =>
      api<Run>("research", {
        method: "POST",
        body: JSON.stringify({
          request_id: crypto.randomUUID(),
          query: question.trim(),
          acknowledge_cost: approved,
        }),
      }),
    retry: false,
    onSuccess: () => {
      setApproved(false);
      client.invalidateQueries({ queryKey: ["research"] });
    },
    onError: () => {
      client.invalidateQueries({ queryKey: ["research"] });
    },
  });
  return (
    <>
      <PageHeader
        eyebrow="Research desk"
        title="Find the source. Check the claim."
        description="Investigate benchmark methodology, pricing changes and missing model facts with cited web research."
      />
      <div className="info-callout">
        <ShieldCheck size={19} />
        <div>
          <strong>A research note is not a verified fact</strong>Findings stay
          separate from the catalog. Nothing changes prices, scores or model
          identities automatically. Open each cited source and review its
          methodology.
        </div>
      </div>
      {query.isPending ? (
        <Loading />
      ) : isPrivateLocked(query.error) ? (
        <PrivateGate />
      ) : query.error ? (
        <ErrorState error={query.error} retry={query.refetch} />
      ) : (
        query.data && (
          <>
            <div className="research-layout">
              <form
                className="panel research-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (approved && query.data?.configured) create.mutate();
                }}
              >
                <div className="research-heading">
                  <ScanSearch size={19} />
                  <h2>Ask a data question</h2>
                  <Badge tone={query.data.configured ? "good" : "warning"}>
                    {query.data.configured ? "Ready" : "API key needed"}
                  </Badge>
                </div>
                <label htmlFor="research-question">
                  What should we investigate?
                </label>
                <textarea
                  id="research-question"
                  placeholder="Why does GDPval-AA show both Elo and win-rate scores? Find the original methodology and explain the difference."
                  value={question}
                  minLength={10}
                  maxLength={1500}
                  required
                  rows={5}
                  onChange={(e) => {
                    setQuestion(e.target.value);
                    setApproved(false);
                  }}
                />
                <div className="research-prompts">
                  {[
                    "Explain GDPval-AA Elo versus win rate using the original methodology.",
                    "Find the documented input, output and cache pricing for Claude Sonnet 4.6.",
                  ].map((text) => (
                    <button
                      key={text}
                      type="button"
                      onClick={() => {
                        setQuestion(text);
                        setApproved(false);
                      }}
                    >
                      {text}
                    </button>
                  ))}
                </div>
                {!query.data.configured && (
                  <div className="research-setup">
                    <Info size={15} />
                    <p>
                      Add <code>OPENAI_API_KEY</code> to the root{" "}
                      <code>.env</code> and restart the API. Keep the key local;
                      don’t paste it into this form.{" "}
                      <Link className="accent" href="/settings">
                        Settings →
                      </Link>
                    </p>
                  </div>
                )}
                <label className="research-approval">
                  <input
                    type="checkbox"
                    checked={approved}
                    required
                    onChange={(e) => setApproved(e.target.checked)}
                  />
                  <span>
                    I approve sending this question to OpenAI and web search.
                    This run may incur API charges.
                  </span>
                </label>
                <button
                  className="button primary"
                  disabled={
                    !query.data.configured ||
                    !approved ||
                    question.trim().length < 10 ||
                    create.isPending ||
                    query.data.runs.some((r) => r.status === "running")
                  }
                >
                  <ScanSearch size={14} />
                  {create.isPending
                    ? "Researching sources…"
                    : "Run cited research"}
                </button>
                {create.error && (
                  <div style={{ marginTop: 16 }}>
                    <ErrorState
                      error={create.error}
                      retry={() => query.refetch()}
                    />
                    <p className="small">
                      Refresh history before starting another request; an
                      interrupted connection may still have incurred charges.
                    </p>
                  </div>
                )}
              </form>
              <aside className="panel research-guardrails">
                <h2>Bounded, manual research</h2>
                <dl>
                  <dt>Research model</dt>
                  <dd>{query.data.model}</dd>
                  <dt>Per request</dt>
                  <dd>Up to 2 web-tool calls and 2,000 output tokens</dd>
                  <dt>Last 24 hours</dt>
                  <dd>
                    Maximum {query.data.daily_limit} attempts, including
                    failures
                  </dd>
                  <dt>Catalog writes</dt>
                  <dd>None</dd>
                </dl>
                <p>
                  These usage caps are not a fixed dollar budget. No automatic
                  retries or scheduled AI runs.
                </p>
                <details>
                  <summary>
                    Search domains ({query.data.domains.length})
                  </summary>
                  <p>{query.data.domains.join(" · ")}</p>
                </details>
              </aside>
            </div>
            <div className="section-row">
              <h2>Research notes</h2>
              <button className="button" onClick={() => query.refetch()}>
                <RefreshCw size={13} />
                Refresh history
              </button>
            </div>
            {!query.data.runs.length ? (
              <Empty title="No research runs yet">
                A manually approved run will appear here with its citations and
                review status.
              </Empty>
            ) : (
              <div className="stack">
                {query.data.runs.map((run) => (
                  <article className="panel research-report" key={run.id}>
                    <header>
                      <div>
                        <h2>{run.query}</h2>
                        <p>
                          {date(run.created_at)} · {run.model}
                        </p>
                      </div>
                      <Badge tone="warning">{humanize(run.status)}</Badge>
                    </header>
                    {run.error && (
                      <p role="alert" className="research-error">
                        {run.error}
                      </p>
                    )}
                    {run.status === "running" && (
                      <p>
                        Research is running. This page will check for the saved
                        result; it will not submit another paid request.
                      </p>
                    )}
                    {run.report && (
                      <>
                        <div className="research-prose">
                          {run.report.blocks.map((parts, i) => (
                            <p key={i}>
                              {parts.map((part, j) =>
                                part.url ? (
                                  <a
                                    key={j}
                                    href={part.url}
                                    title={part.title}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  >
                                    {part.text}
                                  </a>
                                ) : (
                                  <span key={j}>{part.text}</span>
                                ),
                              )}
                            </p>
                          ))}
                        </div>
                        <div className="research-sources">
                          {run.report.sources.map((source) => (
                            <a
                              key={source.url}
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <ExternalLink size={12} />
                              {source.title}
                            </a>
                          ))}
                        </div>
                        <p className="small">
                          Unverified research note ·{" "}
                          {run.report.usage.input_tokens ?? "Unknown"} input
                          tokens / {run.report.usage.output_tokens ?? "unknown"}{" "}
                          output tokens · not imported into the catalog
                        </p>
                      </>
                    )}
                  </article>
                ))}
              </div>
            )}
          </>
        )
      )}
    </>
  );
}
