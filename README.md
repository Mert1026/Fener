# Fener

Source-backed AI model intelligence: discover models, inspect provider deployments, compare workload costs, trace changes, and investigate claims with cited research.

**Every number needs a source.** Canonical models are separate from serving deployments. An access gateway is not automatically the inference provider. Unknown prices, capabilities and benchmark methodology remain unknown.

## Run locally

Requires Python 3.12+, uv, Node 24 with npm and Docker Desktop with the Linux engine running. A global pnpm installation is optional: the launcher uses `npx` to obtain the exact version pinned in `package.json` when pnpm is missing. The first use needs access to the npm registry.

From the project root, you can use:

```sh
npm run setup
npm start
```

Run setup once on a new checkout (or after dependency/schema changes). `npm start` launches the local development API, web app and scheduler; it is not the production Next.js server. It uses uv to select the project's Python environment, so you do not need to activate `.venv` manually. Keep Docker Desktop and the configured PostgreSQL database running. If the database container is stopped, run `docker compose up -d --wait db` first.

This repository uses **pnpm workspaces**: setup installs the locked web and Python dependencies. `npm install` at the root does not install the full application; use setup or `pnpm install --frozen-lockfile` for the JavaScript workspace. `npm run dev` starts only the web frontend. Stop any previously launched Fener services before starting another full stack.

The equivalent Python commands are:

```sh
python scripts/manage.py setup
python scripts/manage.py dev
```

Open [Fener](http://127.0.0.1:3000) or [interactive API documentation](http://127.0.0.1:8000/docs). Setup creates a local `.env` with a random administration key, installs locked dependencies, starts PostgreSQL and applies migrations. Existing `.env` files are never overwritten. The development command starts API, web and scheduler; Ctrl+C stops those processes. Source syncs do not call inference APIs.

For an explicit lightweight fallback on a **new checkout**, use `setup --sqlite`. PostgreSQL is the target database and has a dedicated integration test. Windows may reserve port 5432; see [development](docs/development.md) to choose another loopback port.

```sh
python scripts/manage.py sync --source models_dev
python scripts/manage.py sync --source models_dev
python scripts/manage.py sync --source litellm
python scripts/manage.py check
```

## What is implemented

- Real models.dev and LiteLLM adapters, raw snapshots, conditional fetching, failure isolation, scheduled and manually queued syncs.
- Canonical catalog, conservative identity matching, audited deployment identity corrections, append-only fact and price history, source precedence, conflicts and market events.
- Overview, model explorer/detail, providers/detail, comparison with deployment selection, cost calculator, benchmarks, market feed and deterministic recommendations with constraints, coverage and fallback chains.
- Market cards with readable rates and directional changes. Numerically equivalent prices do not create change events; existing formatting-only events are hidden without deleting audit history.
- Benchmark browsing by name **and reported metric**, with original report links, dates and explicit evidence gaps. Elo and win-rate scores are never shown as one ranking.
- Optional, private AI research with clickable citations, explicit approval per run and usage caps. A separate **Update all benchmarks** action queues cited research for every resolved catalog model. Only complete benchmark claims enter a separate unverified table; prices, identities and other catalog facts never change automatically. Harness/evaluation screens are removed for now; their API operations are disabled by default and existing data is preserved.
- Price/quality normalization and Pareto calculation **only when comparable versioned evidence exists**. Missing methodology produces an explained empty state, never invented points.
- Same-origin authenticated server proxy, signed expiring sessions, private API boundaries, source allowlists, body limits, rate limits, backups, catalog-only exports and CI.

The current live catalog was fetched from real sources. There is no production seed or synthetic leaderboard. Tests use small, labelled fixtures.

## Optional AI research

Add `ZAI_API_KEY` to the ignored root `.env`, restart Fener, unlock Settings with your local `FENER_ADMIN_KEY`, and open **AI research**. Never paste the key into research questions. Every run sends the approved question to Z.ai and may incur charges. This is Fener's only provider API key. Public catalog syncs work without it.

Each approved run makes one Z.ai `search-prime` request followed by one cited summary, capped at 8,000 output tokens. Z.ai uses its **general API**, not the Coding Plan endpoint. Model and search access/credit must be available on that account. Z.ai may retrieve broadly; Fener filters results to approved domains before summarization, and does not fetch the full pages. No qualifying excerpts means no summary call.

Benchmark pages use only complete benchmark claims produced by the catalog-wide AI update. Public catalog feeds and ordinary manual research notes do not populate benchmarks. Pressing **Update all benchmarks** queues every resolved model for one Artificial Analysis domain-filtered search and one bounded summary; progress is durable and visible. The primary metric is the model-level Artificial Analysis Intelligence Index. Coding Agent Index results are rejected because harness and execution settings affect them. Extracted claims require an exact catalog model-name match and citation, remain labeled unverified, and are grouped by exact benchmark name, version, evaluator and metric. Models without published coverage remain `no_evidence`; scores are never guessed to force catalog-wide coverage. A full refresh can make two provider requests per model and may take hours or incur substantial charges.

`FENER_RESEARCH_DAILY_LIMIT` defaults to five manual Z.ai attempts in the last 24 hours, including failed/uncertain attempts. This manual-note cap does not limit the separately approved catalog-wide benchmark queue and is not a dollar budget. Approval is tied to the displayed model. No automatic retries, fallbacks or scheduled AI runs occur. Saved notes and extracted benchmarks remain unverified and never overwrite prices, identities or historical evidence. See [research and security](SECURITY.md).

## Source coverage and limits

OpenRouter, LLM Stats and OpenAI integrations are removed. Old source evidence is retained for provenance and marked retired, but cannot be fetched, queued or scheduled. AI-researched benchmark claims remain unverified, so Fener still has no trustworthy cross-model quality ranking. Serving performance and provider policies remain unknown when the active public sources do not supply them. Cost estimates use listed flat rates and disclose excluded tiers, taxes and fees.

This is a working foundation, not a claim that every advanced feature in the product vision is finished. [Implementation status](docs/status.md) records the remaining work and validation limits.

## Documentation

- [Development and commands](docs/development.md)
- [Architecture](docs/architecture.md) and [data model](docs/data-model.md)
- [Sources, contracts and attribution](docs/sources.md)
- [API and research integration](docs/api.md)
- [Scoring and cost methodology](docs/scoring.md)
- [Operations, backup and restore](docs/operations.md)
- [Security and privacy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Executed validation and limits](docs/validation.md)

Stack: Next.js / React / TypeScript, FastAPI / SQLAlchemy / Alembic, PostgreSQL, Python worker, pnpm and uv. The existing repository license is preserved. Source datasets have their own attribution and reuse conditions; the repository license does not relicense them.
