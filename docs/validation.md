# Validation record — 2026-08-31

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
