# API

FastAPI serves versioned REST resources under `/api/v1`. Interactive documentation: `http://127.0.0.1:8000/docs`. The generated contract is `docs/openapi.json`; TypeScript types are generated into `apps/web/lib/api-schema.d.ts`.

## Public market resources

- `GET /models`: bounded pagination (`limit` ≤100, `offset`), search, publisher/provider/capability filters, minimum context, open weights and sorting. Canonical models by default; `include_unresolved=true` includes candidates.
- `GET /models/{id}`: intrinsic facts, deployment evidence, benchmark results.
- `GET /models/{id}/deployments`, `/models/{id}/pricing`.
- `GET /deployments`, `/providers`, `/providers/{id}`.
- `GET /benchmarks`, `/market-events`, `/sources`, `/overview`.
- `GET /observations/{id}`: normalized value, original source record and snapshot reference.
- `POST /deployments/{id}/cost`: workload calculation with assumptions.
- `POST /recommendations/preview`: bounded read-only deterministic ranking.

Prices serialize as decimal strings, never binary floating-point money. Dates use ISO timestamps. Unknown fields are null or absent, never fabricated zeros. Error envelopes contain `code`, `message`, and where available `request_id`.

## Private resources

Send `Authorization: Bearer <FENER_ADMIN_KEY>`. Unconfigured authentication disables private access rather than making it public.

- `GET /data-health`: ingestion run summaries and disagreements.
- `POST /recommendations`: audited ranking.
- `GET/POST /harnesses`: registered systems, roles and observed usage summaries.
- `POST /harnesses/roles/{id}/policies`: immutable configuration version, initially draft.
- `POST /harnesses/policies/{id}/approve`: explicit `approve: true`, deployment identifier and human note. Never called automatically.
- `POST /telemetry/runs`: validated usage, no prompt content. `(harness_id, external_run_id)` is idempotent; changed contents for the same identifier return 409.
- `GET /telemetry/runs`: recent private usage.
- `GET /evaluations`, `POST /evaluations/suites`, `POST /evaluations/runs`.

## Harness example

```python
import os
import httpx

with httpx.Client(base_url="http://127.0.0.1:8000/api/v1", headers={
    "Authorization": f"Bearer {os.environ['FENER_ADMIN_KEY']}"
}) as client:
    response = client.post("/recommendations", json={
        "task": "researcher",
        "required_capabilities": ["tool_calling"],
        "min_context": 100000,
        "budget": "100",
        "weights": {"price": "1"},
        "workload": {"requests": 10000, "input_tokens": 2000, "output_tokens": 500}
    })
    response.raise_for_status()
    result = response.json()
    # No candidate is a valid result; do not silently relax hard constraints.
    print(result["recommended"])
```

## Evaluation execution

The platform scores submitted outputs. It does not spend money calling inference APIs. Create a suite version with cases (`input`, `reference`, `scorer`); supported scorers are `exact_match`, `contains`, and `human`. Submit exactly one output per case with a deployment identifier and evaluator version. Human scoring requires an explicit [0,1] rating. Results are private and preserve scorer versions and outputs for reproducibility.
