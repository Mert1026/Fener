# Validation record — 2026-08-31

## Data focus, manual research and credential remediation

- Final full check: 68 backend tests passed with PostgreSQL integration enabled, 12 frontend tests passed, and Ruff, mypy, TypeScript, ESLint and the production build passed. OpenAPI freshness, Compose configuration and authored-file formatting checks also passed. The old database password was explicitly rejected after rotation; schema revision is `a708b414fa98`, with 121,040 stored facts and zero research attempts.
- Decimal-equivalent prices now avoid duplicate facts, price observations, conflicts and market-change events. The live audit identified 926 legacy formatting-only price events; the feed excludes them before pagination and retains every stored event. Regression tests also preserve real small changes, quantity normalization and price reversions.
- GDPval-AA contained both Elo (up to 1,932) and win rate (14) in one name group. The UI now separates reported metrics, links original reports, shows dates and explains missing methodology. The catalog exposes 133 name/metric groups from 101 benchmark names. Aider's 3.6–88 score gap is retained as reported evidence, not guessed to be a normalization error. Benchmark observations remain unverified when methodology is missing; no claim that every source score is correct is made.
- Harness/evaluation navigation and pages are removed; authenticated legacy operations default to 410 while database history remains intact. Source sync and identity-review operations remain available.
- Manual research is implemented with private access, cost approval, citations, idempotency, usage caps and no catalog writes. Tests cover missing keys, approval, daily limits, no duplicate charges from automatic retries, failed/uncertain outcomes, citation validation and a mocked HTTP transport. Live OpenAI research was not run: no local API key is configured and no paid requests were made. The live private research endpoint reports zero runs and a missing-key state.
- Interactive browser checks covered real price cards, up/down arrows, source links, the GDPval-AA group switch, original win-rate evidence, locked research access, mobile navigation and dark/light layouts. The 390px viewport has no page-level horizontal overflow; the benchmark table and filter tabs scroll within their containers. Browser console inspection found no errors. Viewport/theme were restored afterward. Research form approval and missing-key behavior are component-tested; no live provider-generated note was visually verified.
- Removed committed database password defaults from Compose, settings, setup and CI. Setup now generates unique matching database credentials; CI generates and masks a disposable password. The active local PostgreSQL password was rotated, preserving other `.env` settings and database data. The local environment remains Git-ignored; a scan of tracked files found no active configured credentials. This is not a claim that GitGuardian incidents or old Git history were erased. No history rewrite, force push or scanner suppression was performed.
- A pre-rotation PostgreSQL/snapshot backup is saved under `.data/backups/20260831T202713656627Z`. Docker's recurring socket startup failure was repaired by moving only its verified socket-only `run` directory to `%LOCALAPPDATA%/Docker/run.fener-backup-20260831-3`; volumes and settings were preserved. The database container was recreated with the updated environment while retaining its existing volume. The additive research migration applied and Alembic reports no drift.
- Formatter commands now target authored project paths, avoiding inaccessible ignored Windows test-cache directories. The original `.ai-harness` files committed during the session are left untouched.

Earlier validation below describes previous builds and their original test counts.

## Executed

- `python scripts/manage.py check`: 44 backend tests passed with PostgreSQL integration enabled; 7 web tests passed; Ruff, mypy, TypeScript, ESLint and the production Next.js build passed.
- PostgreSQL 17.9 runs in Docker on loopback port 15432. Fresh PostgreSQL migrations, schema drift, exact NUMERIC prices and repeated ingestion are tested in an isolated schema. Fresh SQLite migrations and schema checks also passed.
- The original SQLite catalog was transferred transactionally into empty PostgreSQL. Every table's count was checked; original identifiers and history were preserved. The original database and its backup remain local.
- models.dev, OpenRouter and LiteLLM were fetched live. The PostgreSQL models.dev refresh processed 7,857 records, detected two changed source records and retained six new fact observations. No production fixtures were inserted.
- Current catalog: 363 resolved canonical models, 9,786 deployments, 272 providers and 120,997 fact observations. Ambiguous source candidates remain separate.
- All 25 stored snapshot hashes were checked against their database metadata.
- PostgreSQL backup and catalog-only export completed. Output remains under ignored `.data` directories.
- The PostgreSQL backup was restored into a uniquely named disposable database. Every table count and all backup snapshot hashes matched; the live database was only read and the test database was removed afterward.
- API image build and container-to-PostgreSQL read smoke test passed.
- Production JavaScript dependency audit reported no known vulnerabilities; installed Python packages passed compatibility checks.
- Interactive browser checks passed for real model search, two-model selection, deployment-specific costs, recommendation results, price evidence inspection, locked private pages, mobile comparison/overview/navigation, and both themes. The temporary viewport and comparison selections were reset.
- API readiness and overview return 200. The live recommendation endpoint uses `flat-cost-evidence-v2` and enforces explicit opt-in for unresolved identities and zero metered rates.

## Not claimed as executed

The repository Playwright suite was authored and type-checked, but not run through its CLI. Equivalent critical flows were exercised in the in-app browser. Remote CI was not run because no branch was pushed. A live cutover to a restored database and a long-duration containerized worker test were not performed.

LLM Stats live access remains blocked on a local API key. Its benchmark-detail contract is not guessed. OpenRouter's additional benchmark endpoint returned 401 without credentials. There is no fabricated normalized quality ranking.

The backend test run has one upstream Starlette deprecation warning concerning its current httpx test-client integration; it does not fail tests. This validation is a record of the current local build, not a production availability or security guarantee.

## Fenerbahçe colors and chart interaction update

- Applied the requested navy `#002D72` and yellow `#FFED00`, including a yellow wordmark, mark and browser icon. Checked both themes in the browser; light mode keeps the navy sidebar and uses navy chart points for contrast.
- Added context/cost zoom buttons, wheel/pinch zoom, panning, independent axis sliders and reset. Browser checks exercised 2× and 4× zoom, zoom out and full-range reset, including the 390px mobile layout. Wheel, pinch and slider gestures were not separately exercised. Identical coordinates are disclosed as overlapping; values are not jittered or invented.
- Clarified harness, evaluation and source configuration descriptions. These edits do not introduce an AI research agent or inference executor.
- Re-ran all checks: 44 backend tests including PostgreSQL, 7 web tests, lint/types/formatting and the production build passed. Alembic reported no schema drift. The live source-status API returned successful models.dev, OpenRouter and LiteLLM imports, with LLM Stats still requiring a key.

## Root startup shortcuts

- Added `npm run setup` and `npm start` as uv-backed shortcuts for the existing setup and full development launcher. Dependency installation remains pnpm/uv; no manual virtual-environment activation is needed.
- Exercised `npm start`: PostgreSQL was healthy, the API and Next.js started, and the scheduler emitted its startup event. The web page, API readiness and proxied overview all returned 200.
- A second `npm start` exited with status 1 and a clear occupied-port message before launching children. Startup failures now propagate nonzero status, and Windows cleanup targets the launcher's own child process trees rather than only their uv/pnpm wrappers.

## Startup without global pnpm

- Reproduced the user's command environment with pnpm absent from PATH. The launcher now falls back through npx to the exact `packageManager` version, and resolves required commands before spawning services. Web startup calls the workspace directly to avoid recursive launcher scripts.
- `npm run setup` completed in that environment: locked dependencies, healthy PostgreSQL and migrations. The full check command passed with 43 backend tests (PostgreSQL skipped while Docker was unavailable), 7 web tests, lint/types and production build. After Docker recovery, the PostgreSQL integration test separately passed and Alembic reported no drift. Fresh test caches were used because the normal Windows pytest cache had incompatible permissions in the verification environment.
- A bounded `npm start` check without global pnpm returned 200 for the web page, API readiness and proxied overview, which still reported 363 canonical models. Its own process tree was stopped afterward and ports 3000/8000 were verified free for the user's terminal.
- Docker Desktop independently failed on inaccessible zero-byte AF_UNIX socket reparse points, matching this [upstream report](https://github.com/docker/desktop-feedback/issues/460). With Docker stopped, only verified socket-only runtime directories were renamed to sibling backups: `%LOCALAPPDATA%/Docker/run.fener-backup-20260831`, `%LOCALAPPDATA%/Docker/run.fener-backup-20260831-2`, and `%LOCALAPPDATA%/docker-secrets-engine.fener-backup-20260831`. Docker then started successfully. No database volumes, settings or secret contents were changed, and no factory reset was performed.
