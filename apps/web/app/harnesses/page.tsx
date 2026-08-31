"use client";
import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, ShieldCheck } from "lucide-react";
import { api, isPrivateLocked } from "@/lib/api";
import { money } from "@/lib/format";
import { PrivateGate } from "@/components/private-gate";
import { Badge, Empty, ErrorState, Loading, PageHeader } from "@/components/ui";
type Harness = {
  id: string;
  name: string;
  description: string;
  runs: number;
  observed_spend: string | null;
  success_rate: number | null;
  mean_duration_ms: number | null;
  roles: { id: string; name: string; default_deployment_id: string | null }[];
};
export default function HarnessesPage() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [open, setOpen] = useState(false);
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["harnesses"],
    queryFn: () => api<Harness[]>("harnesses"),
    retry: false,
  });
  const create = useMutation({
    mutationFn: () =>
      api("harnesses", {
        method: "POST",
        body: JSON.stringify({ name, description }),
      }),
    onSuccess: () => {
      setName("");
      setDescription("");
      setOpen(false);
      client.invalidateQueries({ queryKey: ["harnesses"] });
    },
  });
  return (
    <>
      <PageHeader
        eyebrow="Personal intelligence"
        title="Your harnesses"
        description="Model performance in your real workloads. Private telemetry, explicit roles, controlled defaults."
        action={
          <button
            className="button primary"
            disabled={Boolean(query.error)}
            onClick={() => setOpen(!open)}
          >
            <Plus size={13} /> Register harness
          </button>
        }
      />
      {query.isPending ? (
        <Loading />
      ) : isPrivateLocked(query.error) ? (
        <PrivateGate />
      ) : query.error ? (
        <ErrorState error={query.error} retry={query.refetch} />
      ) : (
        <>
          {open && (
            <form
              className="panel settings-panel"
              style={{ marginBottom: 22 }}
              onSubmit={(e) => {
                e.preventDefault();
                create.mutate();
              }}
            >
              <h2>Register a harness</h2>
              <div className="field">
                <label htmlFor="harness-name">Name</label>
                <input
                  id="harness-name"
                  required
                  maxLength={200}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="harness-description">Description</label>
                <input
                  id="harness-description"
                  maxLength={2000}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <p>
                Creates researcher, coder, reviewer and router roles. No default
                is applied automatically.
              </p>
              <button className="button primary" disabled={create.isPending}>
                Create harness
              </button>
              {create.error && <p role="alert">{create.error.message}</p>}
            </form>
          )}
          {query.data?.length ? (
            <div className="stack">
              {query.data.map((harness) => (
                <section className="panel" key={harness.id}>
                  <div className="panel-header">
                    <div>
                      <h2>{harness.name}</h2>
                      <p>{harness.description || harness.id}</p>
                    </div>
                    <Badge>
                      <ShieldCheck size={10} /> Private
                    </Badge>
                  </div>
                  <div className="panel-content">
                    <div className="stats-grid">
                      {[
                        { label: "Reported runs", value: harness.runs },
                        {
                          label: "Observed spend",
                          value: money(harness.observed_spend),
                        },
                        {
                          label: "Success rate",
                          value:
                            harness.success_rate == null
                              ? "Not measured"
                              : `${(harness.success_rate * 100).toFixed(1)}%`,
                        },
                        {
                          label: "Mean duration",
                          value:
                            harness.mean_duration_ms == null
                              ? "Not measured"
                              : `${Math.round(harness.mean_duration_ms)} ms`,
                        },
                      ].map((stat) => (
                        <div className="stat" key={stat.label}>
                          <div className="stat-label">{stat.label}</div>
                          <div
                            className="stat-value mono"
                            style={{ fontSize: 21 }}
                          >
                            {stat.value}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Role</th>
                            <th>Identifier</th>
                            <th>Default deployment</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {harness.roles.map((role) => (
                            <tr key={role.id}>
                              <td>{role.name}</td>
                              <td className="mono muted">{role.id}</td>
                              <td>
                                {role.default_deployment_id ??
                                  "No approved default"}
                              </td>
                              <td>
                                <Link href="/find" className="accent">
                                  Find candidates →
                                </Link>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="small" style={{ marginTop: 15 }}>
                      Harness ID: <code>{harness.id}</code>. Report usage
                      through <code>POST /api/v1/telemetry/runs</code>. Prompt
                      content is rejected by the schema.
                    </p>
                  </div>
                </section>
              ))}
            </div>
          ) : (
            <Empty title="A place for your own evidence">
              Register a harness, report telemetry through the API, then
              evaluate candidates against your actual tasks.
            </Empty>
          )}
          <div className="info-callout" style={{ marginTop: 22 }}>
            <ShieldCheck size={16} />
            <div>
              <strong>Policies require explicit approval</strong>Create
              versioned role policies through the authenticated API. A human
              approval step is required before changing any default deployment.
            </div>
          </div>
        </>
      )}
    </>
  );
}
