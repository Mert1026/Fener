"use client";
import { useState } from "react";
import Link from "next/link";
import { Check, Copy, ExternalLink } from "lucide-react";
import type { Deployment } from "@/lib/api";
import { money, tokens } from "@/lib/format";
import { DeploymentAnalytics } from "./analytics";
import { Badge, EvidenceValue } from "./ui";
export function DeploymentTable({
  deployments,
}: {
  deployments: Deployment[];
}) {
  const [copied, setCopied] = useState<string | null>(null);
  return (
    <>
      <DeploymentAnalytics deployments={deployments} />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Access / upstream</th>
              <th>API model ID</th>
              <th>Input / 1M</th>
              <th>Output / 1M</th>
              <th>Cache / 1M</th>
              <th>Context</th>
              <th>Availability</th>
            </tr>
          </thead>
          <tbody>
            {deployments.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>
                    {row.provider_url ? (
                      <a
                        className="provider-link"
                        href={row.provider_url}
                        target="_blank"
                        rel="noreferrer"
                        title={`Open ${row.access_provider} documentation`}
                      >
                        {row.access_provider}
                        <ExternalLink size={11} aria-hidden />
                      </a>
                    ) : (
                      <Link
                        className="provider-link"
                        href={`/providers/${row.access_provider}`}
                        title={`Open ${row.access_provider} in Fener`}
                      >
                        {row.access_provider}
                      </Link>
                    )}
                  </strong>
                  <small
                    className="muted"
                    style={{ display: "block", marginTop: 5 }}
                  >
                    {row.upstream_provider ? (
                      <Link
                        className="provider-link muted-link"
                        href={`/providers/${row.upstream_provider}`}
                      >
                        {row.upstream_provider}
                      </Link>
                    ) : (
                      "Upstream unknown"
                    )}
                  </small>
                  {row.listing_kind === "routing_quote" && (
                    <Badge tone="warning">Routing quote</Badge>
                  )}
                </td>
                <td>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 7 }}
                  >
                    <span className="mono" title={row.api_model_id}>
                      {row.api_model_id.length > 40
                        ? row.api_model_id.slice(0, 38) + "…"
                        : row.api_model_id}
                    </span>
                    <button
                      className="icon-button"
                      aria-label={`Copy ${row.api_model_id}`}
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(row.api_model_id);
                          setCopied(row.id);
                        } catch {
                          setCopied(null);
                        }
                      }}
                    >
                      {copied === row.id ? (
                        <Check size={12} />
                      ) : (
                        <Copy size={12} />
                      )}
                    </button>
                  </div>
                </td>
                {["input_tokens", "output_tokens", "cached_input"].map(
                  (metric) => (
                    <td key={metric}>
                      <EvidenceValue fact={row.facts[`price.${metric}`]}>
                        <span className="mono">
                          {money(
                            (
                              row.facts[`price.${metric}`]?.value as
                                { amount: string } | undefined
                            )?.amount,
                          )}
                        </span>
                      </EvidenceValue>
                    </td>
                  ),
                )}
                <td>
                  <EvidenceValue fact={row.facts.context_window}>
                    <span className="mono">
                      {tokens(
                        row.facts.context_window?.value as number | undefined,
                      )}
                    </span>
                  </EvidenceValue>
                </td>
                <td>
                  <EvidenceValue fact={row.facts.availability} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
