# Implementation status

This document distinguishes working features from the broader product vision. It is not a roadmap disguised as completed functionality.

## Working foundation

Real models.dev, OpenRouter and LiteLLM ingestion; a credential-gated LLM Stats catalog adapter; raw snapshots and fetch receipts; source-scoped model aliases; explicit canonical identities; provider/access/endpoint separation; append-only facts, prices, conflicts and events; per-field confirmation freshness; durable manual sync requests; scheduled polling; deployment identity correction with review evidence and audit history.

Typed catalog API and generated TypeScript schemas; all main navigation views; server-side model filtering and paging; configurable table columns; local comparison selections; deployment-specific flat-rate costing; source evidence views; historical prices; deterministic recommendation constraints, explicit weights, missing-evidence coverage and fallback chains. Quality normalization and Pareto calculations reject incomplete methodology. There is no fake quality scatter.

The market feed displays readable cards and numerical price changes, filtering formatting-only events while preserving stored history. Benchmark groups separate score units, retain original report links/dates and surface missing methodology. No source score is guessed or silently rescaled.

Private manual AI research supports OpenAI Responses and Z.ai search plus cited summaries, explicit provider/model approval, local usage limits and no retries or fallback. Notes remain unverified and cannot update the catalog. Live provider execution requires the selected provider's key and account access; only mocked provider flows have been tested. A Z.ai key does not authenticate OpenRouter or LLM Stats catalog endpoints. Harness and evaluation screens are removed for now; their authenticated API operations are paused by default and existing history remains intact.

## Still gated or intentionally unfinished

| Area                 | Current limit / next step                                                                                                                                                                                                |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| LLM Stats            | Supply a local API key and verify the authenticated benchmark-detail contract before implementing that ingestion. No fabricated payload or guessed endpoint is used.                                                     |
| Quality intelligence | Current ingested benchmark rows lack sufficient version/evaluator/scale metadata. The quality frontier remains empty; a trustworthy cross-model benchmark comparison needs better evidence.                              |
| Endpoint performance | OpenRouter endpoint fetches are a bounded sample. No measured latency/throughput series is available in the current sample. Uptime data is retained when present.                                                        |
| Identity resolution  | Exact matching and audited deployment overrides work. Bulk review suggestions and a dedicated merge-review UI are not implemented; uncertain identities remain separate.                                                 |
| Conflict review      | Both observations and deterministic precedence are inspectable. User-configured field authority policies and a manual conflict-winner workflow are not implemented.                                                      |
| Cost tiers           | Flat source rates, cache and supported usage components work. Context tiers, batch discounts and provider-specific billing rules need explicit source contracts.                                                         |
| Internal learning    | Telemetry and evaluation history are stored separately from public evidence. Statistical confidence intervals, learned role preferences, savings analysis and automatic candidate-evaluation queues are not implemented. |
| Evaluation execution | Paused by default. UI removed; legacy tables and implementation are preserved for a possible later return. No paid evaluation executor is implemented.                                                                   |
| Notifications        | No external messaging, watchlist notifications or automated recommendations are sent.                                                                                                                                    |
| Public hosting       | No deployment, public accounts, tenancy, public-data licensing review or production monitoring stack is configured.                                                                                                      |

## Validation

Backend tests cover source contracts, normalization, idempotence, price reversions, precedence/conflicts, stale confirmation, source failure, credentials, snapshots, retry timing, costing, constraints, Pareto ties, authentication, telemetry, policy approval, evaluations, queue deduplication and identity audits. PostgreSQL integration applies migrations in an isolated schema, checks schema drift and verifies exact NUMERIC prices and idempotence. Fresh SQLite migrations are also checked.

Frontend tests cover numeric formatting, unknown versus free, table selection, columns, signed-session expiry and same-origin boundaries. Production builds, strict TypeScript and ESLint are checked. Interactive browser acceptance uses real local catalog data. CI is configured, but a remote CI run requires a future push; nothing was pushed by the build task.

The API container image builds successfully and its database access is smoke-tested. PostgreSQL backup, restoration into a disposable database, snapshot integrity and catalog exports are exercised. Live recovery cutover and long-running containerized worker operation still need acceptance testing before relying on a deployed installation. The currently exercised stack is local Node/Python services with PostgreSQL in Docker.
