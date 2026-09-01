# API

FastAPI serves versioned REST resources under `/api/v1`. Interactive documentation: `http://127.0.0.1:8000/docs`. The generated contract is `docs/openapi.json`; TypeScript types are generated into `apps/web/lib/api-schema.d.ts`.

## Public market resources

- `GET /models`: bounded pagination (`limit` ≤100, `offset`), search, publisher/provider/capability filters, minimum context, open weights and sorting. Canonical models by default; `include_unresolved=true` includes candidates.
- `GET /models/{id}`: intrinsic facts, deployment evidence, benchmark results.
- `GET /models/{id}/deployments`, `/models/{id}/pricing`.
- `GET /deployments`, `/providers`, `/providers/{id}`.
- `GET /benchmarks` (optional `group_id`) and `/benchmarks/groups`: latest source-confirmed observations grouped by benchmark name and reported score metric. Report URL/date and methodology gaps accompany results.
- `GET /market-events`: material events, filtering legacy equivalent-price changes before pagination. Values remain structured in the API; the UI formats them as cards.
- `GET /sources`, `/overview`.
- `GET /observations/{id}`: normalized value, original source record and snapshot reference.
- `POST /deployments/{id}/cost`: workload calculation with assumptions.
- `POST /recommendations/preview`: bounded read-only deterministic ranking.
- `GET /analytics/benchmarks`: comparable normalized evidence, separated by exact version and evaluator.
- `POST /analytics/frontier`: cost/quality dominance among candidates with complete comparable evidence and the same constraints.

Prices serialize as decimal strings, never binary floating-point money. Dates use ISO timestamps. Unknown fields are null or absent, never fabricated zeros. Error envelopes contain `code`, `message`, and where available `request_id`.

## Private resources

Send `Authorization: Bearer <FENER_ADMIN_KEY>`. Unconfigured authentication disables private access rather than making it public.

- `GET /research`: configured provider/name/model, required key-variable name, local limits, source policy and private history; never returns provider keys. `configured` indicates a local key exists, not verified account access or credit.
- `POST /research`: `request_id` (UUID), `provider: "zai"`, `model`, `query` (10–1,500 characters), and `acknowledge_cost: true`. The approved model must match current server configuration; mismatch returns 409 before any Z.ai call. Requires local `ZAI_API_KEY`. Returns a saved note/status, never a catalog mutation. Reusing an ID returns its existing attempt; a different query/model for that ID conflicts. Daily limits include unsuccessful attempts. Connection failures can leave an `uncertain` result and are never retried automatically. Historical notes retain their original provider label.

`GET /benchmark-refresh` returns the latest private catalog-wide refresh status. `POST /benchmark-refresh` requires `request_id` and `acknowledge_cost: true`; it snapshots every resolved catalog model into a durable queue and returns 202 without waiting for provider calls. The worker processes one model at a time with at most one search and one 2,000-token summary, never retries failed or uncertain items, and reports model/result/failure progress. Complete claims enter `research_benchmarks` only when the cited evidence ID is valid and the returned model name exactly matches the queued catalog model. `GET /benchmarks`, model-detail benchmark lists and `GET /benchmarks/groups` expose only those AI-researched rows. They are always `ai_extracted_unverified`; legacy catalog benchmark rows are hidden, and normalized benchmark analytics exclude every unreviewed AI extraction.

Harness, telemetry and evaluation operations listed below are **paused** and return 410 after authentication unless deliberately re-enabled on the server. The web proxy does not expose them. Existing stored data remains intact. Source jobs and identity review operations continue to work.

- `GET /data-health`: ingestion run summaries and disagreements.
- `POST /recommendations`: audited ranking.
- `GET/POST /harnesses`: registered systems, roles and observed usage summaries.
- `POST /harnesses/roles/{id}/policies`: immutable configuration version, initially draft.
- `GET /harnesses/roles/{id}/policies`: review versioned configurations and approvals, including the deployment chosen at approval time.
- `POST /harnesses/policies/{id}/approve`: explicit `approve: true`, deployment identifier and human note. Never called automatically.
- `POST /telemetry/runs`: validated usage, no prompt content. `(harness_id, external_run_id)` is idempotent; changed contents for the same identifier return 409.
- `GET /telemetry/runs`: recent private usage.
- `GET /evaluations`, `POST /evaluations/suites`, `POST /evaluations/runs`.
- `GET/POST /internal/sync`: durable manual source jobs; POST takes a configured `source_id`.
- `POST /internal/deployments/{id}/identity`: audited canonical assignment with `target_model_id`, `evidence_url` and a review `note`; it does not delete historical model facts.
- `GET /internal/identity-overrides`: identity review history.

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

This feature is paused. Its retained implementation scores submitted outputs without calling inference APIs. Supported scorers are `exact_match`, `contains`, and `human`; historical results remain private. Manual AI research is separate and may incur charges only after approval.
