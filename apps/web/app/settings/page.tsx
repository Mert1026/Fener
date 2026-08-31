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
            file to access harnesses, evaluations and detailed data health.
            Provider API keys stay on the server. The browser receives an
            HttpOnly session cookie.
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
          <h2>Source credentials & scheduling</h2>
          <p>
            Configure server-only values in the root <code>.env</code>, then
            restart the API and worker.
          </p>
          <pre className="code-block">{`LLM_STATS_API_KEY=…\nOPENROUTER_API_KEY=…  # optional for public catalogs\nFENER_SYNC_INTERVAL_SECONDS=21600\nFENER_OPENROUTER_ENDPOINT_LIMIT=20`}</pre>
          <p style={{ marginTop: 17 }}>
            This screen never returns stored secrets. Source sync runs via{" "}
            <code>uv run fener sync</code>; continuous schedules run via{" "}
            <code>uv run fener worker</code>.
          </p>
        </section>
        <section className="panel settings-panel">
          <h2>Controlled policy changes</h2>
          <p>
            Automatic model switching and AI research are disabled.
            Recommendations provide evidence for a human decision. No paid model
            calls run in the background.
          </p>
        </section>
      </div>
    </>
  );
}
