"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/ui";
export default function SettingsPage() {
  const [key, setKey] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const client = useQueryClient();
  async function login(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const response = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.message);
      setKey("");
      setMessage("Private workspace unlocked for this browser session.");
      await client.invalidateQueries();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Unable to unlock workspace.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeader
        eyebrow="Workspace configuration"
        title="Settings"
        description="A local workspace with explicit boundaries between market data and private intelligence."
      />
      <div className="stack">
        <section className="panel settings-panel">
          <ShieldCheck
            size={22}
            className="accent"
            style={{ marginBottom: 15 }}
          />
          <h2>Unlock private intelligence</h2>
          <p>
            Use <code>FENER_ADMIN_KEY</code> from your local <code>.env</code>{" "}
            file to access AI research and detailed data health. Provider API
            keys stay on the server. The browser receives an HttpOnly session
            cookie.
          </p>
          <form onSubmit={login}>
            <div className="field">
              <label htmlFor="admin-key">Workspace administration key</label>
              <input
                id="admin-key"
                type="password"
                autoComplete="current-password"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="Enter your local administration key"
                required
              />
            </div>
            <button className="button primary" disabled={busy}>
              {busy ? "Unlocking…" : "Unlock private workspace"}
            </button>
            <button
              type="button"
              className="text-button"
              onClick={async () => {
                await fetch("/api/session", { method: "DELETE" });
                await client.invalidateQueries();
                setMessage("Private workspace locked.");
              }}
            >
              Lock workspace
            </button>
          </form>
          {message && (
            <p className="notification" role="status">
              {message}
            </p>
          )}
        </section>
        <section className="panel settings-panel">
          <h2>Public data scheduling</h2>
          <p>
            Configure server-only values in the root <code>.env</code>, then
            restart the API and worker.
          </p>
          <pre className="code-block">{`FENER_SYNC_INTERVAL_SECONDS=21600`}</pre>
          <p style={{ marginTop: 17 }}>
            This screen never returns stored secrets. Source sync runs via{" "}
            <code>uv run fener sync</code>; continuous schedules run via{" "}
            <code>uv run fener worker</code>.
          </p>
          <p style={{ marginTop: 17 }}>
            models.dev and LiteLLM are public, read-only catalog feeds and need
            no API key. OpenRouter, LLM Stats and OpenAI integrations are
            removed. Existing evidence from retired sources remains available
            for provenance, but Fener cannot queue or schedule new calls to
            them.
          </p>
        </section>
        <section className="panel settings-panel">
          <h2>Manual AI research</h2>
          <p>
            Search filters the ingested catalog; recommendations use explicit
            rules and evidence. The research desk can make explicitly approved
            Z.ai research calls. Its cited notes stay separate from catalog
            facts. No scheduled AI calls or automatic data changes run.
          </p>
          <pre className="code-block">{`ZAI_API_KEY=…\nFENER_ZAI_RESEARCH_MODEL=glm-4.7-flash\nFENER_RESEARCH_DAILY_LIMIT=5`}</pre>
          <p>
            Z.ai uses its general API for one search and one cited summary per
            approved run. General API/search access may be billed separately
            from a Coding Plan. This is the only API key Fener uses. Complete,
            cited benchmark claims are extracted into the benchmark desk as
            unverified AI data; public catalog feeds do not fill benchmarks.
          </p>
          <p>
            Restart the API after configuring these values. Every research run
            requires approval in the research desk. Harnesses and evaluations
            are paused; existing data is preserved.
          </p>
        </section>
      </div>
    </>
  );
}
