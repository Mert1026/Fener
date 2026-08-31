# Fener

Source-backed AI model intelligence: discover models, inspect provider deployments, compare workload costs, trace changes, and evaluate candidates against your own work.

**Every number needs a source.** Canonical models are separate from serving deployments. An access gateway is not automatically the inference provider. Unknown prices, capabilities and benchmark methodology remain unknown.

## Run locally

Requires Python 3.12+, uv, Node 24, pnpm 11 and Docker Desktop with the Linux engine running.

```sh
python scripts/manage.py setup
python scripts/manage.py dev
```

Open [Fener](http://127.0.0.1:3000) or [interactive API documentation](http://127.0.0.1:8000/docs). Setup creates a local `.env` with a random administration key, installs locked dependencies, starts PostgreSQL and applies migrations. Existing `.env` files are never overwritten. The development command starts API, web and scheduler; Ctrl+C stops those processes. Source syncs do not call inference APIs.

For an explicit lightweight fallback on a **new checkout**, use `setup --sqlite`. PostgreSQL is the target database and has a dedicated integration test. Windows may reserve port 5432; see [development](docs/development.md) to choose another loopback port.

```sh
python scripts/manage.py sync --source models_dev
python scripts/manage.py sync --source openrouter
python scripts/manage.py sync --source litellm
python scripts/manage.py check
```

## What is implemented

- Real models.dev, OpenRouter and LiteLLM adapters, raw snapshots, conditional fetching, failure isolation, scheduled and manually queued syncs.
- Canonical catalog, conservative identity matching, audited deployment identity corrections, append-only fact and price history, source precedence, conflicts and market events.
- Overview, model explorer/detail, providers/detail, comparison with deployment selection, cost calculator, benchmarks, market feed and deterministic recommendations with constraints, coverage and fallback chains.
- Private harnesses, roles, versioned policies with explicit approval, idempotent telemetry, immutable evaluation suites and recorded deterministic or human-scored runs.
- Price/quality normalization and Pareto calculation **only when comparable versioned evidence exists**. Missing methodology produces an explained empty state, never invented points.
- Same-origin authenticated server proxy, signed expiring sessions, private API boundaries, source allowlists, body limits, rate limits, backups, catalog-only exports and CI.

The current live catalog was fetched from real sources. There is no production seed or synthetic leaderboard. Tests use small, labelled fixtures.

## Source coverage and limits

LLM Stats requires `LLM_STATS_API_KEY` in the server `.env`. Its documented catalog adapter is implemented, but authenticated benchmark-detail ingestion is gated until its live response contract can be verified. Current catalog benchmark observations lack sufficient methodology for a trustworthy cross-model quality ranking.

OpenRouter endpoint collection defaults to a deterministic sample of 20 models, not the entire endpoint market. Serving performance and provider policies remain unknown when the sources do not supply them. Cost estimates use listed flat rates and disclose excluded tiers, taxes and fees.

This is a working foundation, not a claim that every advanced feature in the product vision is finished. [Implementation status](docs/status.md) records the remaining work and validation limits.

## Documentation

- [Development and commands](docs/development.md)
- [Architecture](docs/architecture.md) and [data model](docs/data-model.md)
- [Sources, contracts and attribution](docs/sources.md)
- [API and harness integration](docs/api.md)
- [Scoring and cost methodology](docs/scoring.md)
- [Operations, backup and restore](docs/operations.md)
- [Security and privacy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Executed validation and limits](docs/validation.md)

Stack: Next.js / React / TypeScript, FastAPI / SQLAlchemy / Alembic, PostgreSQL, Python worker, pnpm and uv. The existing repository license is preserved. Source datasets have their own attribution and reuse conditions; the repository license does not relicense them.
