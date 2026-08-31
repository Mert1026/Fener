"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, Plus } from "lucide-react";
import { api, isPrivateLocked } from "@/lib/api";
import { date } from "@/lib/format";
import { PrivateGate } from "@/components/private-gate";
import { Badge, Empty, ErrorState, Loading, PageHeader } from "@/components/ui";
type Case = {
  id: string;
  name: string;
  input: string;
  reference: string;
  scorer: string;
};
type Lab = {
  suites: {
    id: string;
    name: string;
    version: string;
    category: string;
    cases: Case[];
  }[];
  runs: {
    id: string;
    suite_id: string;
    deployment_id: string;
    score: string;
    created_at: string;
    evaluator_version: string;
  }[];
};
export default function EvaluationsPage() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["evaluations"],
    queryFn: () => api<Lab>("evaluations"),
    retry: false,
  });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    version: "1",
    category: "general",
    caseName: "",
    input: "",
    reference: "",
    scorer: "exact_match",
  });
  const create = useMutation({
    mutationFn: () =>
      api("evaluations/suites", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          version: form.version,
          category: form.category,
          cases: [
            {
              name: form.caseName,
              input: form.input,
              reference: form.reference,
              scorer: form.scorer,
            },
          ],
        }),
      }),
    onSuccess: () => {
      setOpen(false);
      client.invalidateQueries({ queryKey: ["evaluations"] });
    },
  });
  return (
    <>
      <PageHeader
        eyebrow="The evaluation lab"
        title="Test against your own standard."
        description="Versioned suites, deterministic scoring and explicit human ratings. Internal results stay private."
        action={
          <button
            className="button primary"
            disabled={Boolean(query.error)}
            onClick={() => setOpen(!open)}
          >
            <Plus size={13} /> Create suite
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
              style={{ marginBottom: 25 }}
              onSubmit={(e) => {
                e.preventDefault();
                create.mutate();
              }}
            >
              <h2>A reproducible evaluation suite</h2>
              <div className="form-grid">
                {[
                  { key: "name", label: "Suite name" },
                  { key: "version", label: "Version" },
                  { key: "category", label: "Category" },
                  { key: "caseName", label: "First case name" },
                  { key: "input", label: "Case input" },
                  { key: "reference", label: "Expected output / reference" },
                ].map((field) => (
                  <div className="field" key={field.key}>
                    <label htmlFor={field.key}>{field.label}</label>
                    <input
                      id={field.key}
                      required
                      maxLength={
                        field.key === "input" || field.key === "reference"
                          ? 10000
                          : 100
                      }
                      value={form[field.key as keyof typeof form]}
                      onChange={(e) =>
                        setForm({ ...form, [field.key]: e.target.value })
                      }
                    />
                  </div>
                ))}
                <div className="field">
                  <label htmlFor="scorer">Scorer</label>
                  <select
                    id="scorer"
                    value={form.scorer}
                    onChange={(e) =>
                      setForm({ ...form, scorer: e.target.value })
                    }
                  >
                    <option value="exact_match">Exact match</option>
                    <option value="contains">Contains reference</option>
                    <option value="human">Explicit human rating</option>
                  </select>
                </div>
              </div>
              <p style={{ marginTop: 17 }}>
                Creates a suite with one case. The API supports up to 100 cases
                per immutable version. No model is called.
              </p>
              <button className="button primary" disabled={create.isPending}>
                Create suite
              </button>
              {create.error && <p role="alert">{create.error.message}</p>}
            </form>
          )}
          {query.data?.suites.length ? (
            <div className="provider-grid">
              {query.data.suites.map((suite) => (
                <section className="panel provider-card" key={suite.id}>
                  <div className="provider-top">
                    <FlaskConical size={22} className="accent" />
                    <Badge>v{suite.version}</Badge>
                  </div>
                  <h2>{suite.name}</h2>
                  <p>
                    {suite.category} · {suite.cases.length} cases
                  </p>
                  <details style={{ marginTop: 14 }}>
                    <summary className="small muted">
                      Inspect suite & case identifiers
                    </summary>
                    <pre className="code-block" style={{ marginTop: 12 }}>
                      {JSON.stringify(
                        { suite_id: suite.id, cases: suite.cases },
                        null,
                        2,
                      )}
                    </pre>
                  </details>
                  <footer>
                    <span>Versioned & reproducible</span>
                    <Badge tone="blue">Private</Badge>
                  </footer>
                </section>
              ))}
            </div>
          ) : (
            <Empty title="Your evaluation lab is ready">
              Create a suite, run it in your harness, then submit outputs to the
              API for scoring. There are no simulated results here.
            </Empty>
          )}
          <div className="section-row">
            <h2>Evaluation history</h2>
            <span className="muted small">
              Public benchmarks and internal evaluations stay separate
            </span>
          </div>
          {query.data?.runs.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Suite</th>
                    <th>Score</th>
                    <th>Evaluator version</th>
                    <th>Recorded</th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.runs.map((run) => (
                    <tr key={run.id}>
                      <td className="mono">{run.id.slice(0, 8)}</td>
                      <td>
                        {query.data.suites.find(
                          (suite) => suite.id === run.suite_id,
                        )?.name ?? run.suite_id}
                      </td>
                      <td className="mono">
                        {(Number(run.score) * 100).toFixed(1)}%
                      </td>
                      <td>{run.evaluator_version}</td>
                      <td>{date(run.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="panel settings-panel">
              <h2>Connect an evaluation runner</h2>
              <p>
                Send one output for every case in the selected suite version to{" "}
                <code>POST /api/v1/evaluations/runs</code>. Exact-match and
                contains scorers run deterministically; human-scored cases
                require an explicit rating.
              </p>
              <pre className="code-block">{`{\n  "suite_id": "your suite identifier",\n  "deployment_id": "tested deployment identifier",\n  "evaluator_version": "your-runner-v1",\n  "outputs": [\n    {"case_id": "case identifier", "output": "actual model output"}\n  ]\n}`}</pre>
            </div>
          )}
        </>
      )}
    </>
  );
}
