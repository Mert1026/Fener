# Development

Requires Python 3.12+, uv 0.11.7, Node 24 with npm and Docker Compose with the Linux engine. Python and JavaScript dependencies are locked in `uv.lock` and `pnpm-lock.yaml`. The launcher uses an installed pnpm or falls back to `npx --yes pnpm@11.19.0`, reading the pinned version from `package.json`; no global pnpm installation is required. The first fallback use needs npm registry access.

## First start

Run `python scripts/manage.py setup`, then `python scripts/manage.py dev` from the repository. Setup is safe to repeat: it preserves your `.env`, creates `.data`, installs dependencies and applies forward migrations. No default administration password is committed. Find the generated `FENER_ADMIN_KEY` in your local `.env` and enter it in Settings to unlock private views. Do not paste keys into issues, screenshots or chats.

The root shortcuts `npm run setup` and `npm start` run the same commands through uv, so manual virtual-environment activation is unnecessary. `npm start` launches the local API, web and worker; `npm run dev` launches only the web. Dependencies still use pnpm and uv, not `npm install`. Keep Docker Desktop and the configured database running; restart a stopped database with `docker compose up -d --wait db` before launching the app. Do not launch a second stack over services already using ports 3000 and 8000.

The API listens on `127.0.0.1:8000`, web on `127.0.0.1:3000`, and PostgreSQL on the configured loopback port. The worker checks schedules every minute; each source defaults to a six-hour interval. A failed source does not prevent other sources from syncing. Stopping the worker leaves manual jobs durably queued.

On Windows, if port 5432 is reserved, set `FENER_POSTGRES_PORT=15432` and change the port in `DATABASE_URL` to 15432 before `docker compose up -d --wait db`. The validated build workspace uses 15432. Never kill another application merely to free a port.

For SQLite on a fresh checkout use `setup --sqlite`. To use an existing fallback database, preserve `.env` with `DATABASE_URL=sqlite:///.data/fener.db`. SQLite preserves exact source decimal strings, but its NUMERIC storage and concurrency differ from PostgreSQL. Financial aggregates and concurrent write behavior must be validated on PostgreSQL.

## Commands

| Command                                             | Purpose                                                              |
| --------------------------------------------------- | -------------------------------------------------------------------- |
| `python scripts/manage.py dev`                      | API, web and scheduled worker                                        |
| `python scripts/manage.py api`                      | API only                                                             |
| `python scripts/manage.py web`                      | Web only                                                             |
| `python scripts/manage.py worker`                   | Scheduler and manual queue                                           |
| `python scripts/manage.py sync --source models_dev` | One real source                                                      |
| `python scripts/manage.py sync`                     | All sources independently; exits nonzero if any fails or needs a key |
| `python scripts/manage.py check`                    | Lint, formatting, types, tests and production build                  |
| `python scripts/manage.py schema`                   | Regenerate OpenAPI and TypeScript schemas                            |
| `python scripts/manage.py backup --docker`          | Back up the Compose PostgreSQL database and snapshots                |
| `python scripts/manage.py export`                   | Catalog-only JSONL and CSV                                           |

Web development updates automatically. Restart the API after Python edits; the combined launcher intentionally avoids a Windows reloader that can leave an old child process running. No hosted site or Git push is part of these commands.

## Database checks

`uv run alembic upgrade head` applies migrations; `uv run alembic check` verifies metadata matches them. The integration test creates and drops a uniquely named **test schema**, never the application schema. Set `FENER_TEST_POSTGRES_URL` to a test-capable PostgreSQL connection and run `uv run pytest tests/test_postgres.py -q`. CI supplies its own PostgreSQL service. The test is explicitly skipped without that variable.

Migrations also run from a fresh SQLite database. Do not use `create_all` for application schema changes; it is limited to isolated tests. Lossy price-precision downgrades are deliberately refused.

## Browser acceptance

With the API and web running, install the Playwright Chromium runtime (`pnpm --filter @fener/web exec playwright install chromium`) and run `pnpm --filter @fener/web test:e2e`. The catalog scenario needs at least two real ingested models and otherwise skips explicitly; it never seeds the application database. Private access and mobile navigation are also covered. `FENER_E2E_URL` selects another local test installation. Browser traces may contain catalog data and are ignored by Git.

The build session exercised these flows interactively in the in-app browser. The repository Playwright suite is provided for repeatable acceptance, but has not been executed in this build environment; it is not included in the reported passing unit-test count.

## Optional containers

The default Compose file runs PostgreSQL only. `compose.app.yaml` adds API, migration and worker containers; web remains a local Next.js process. Run migrations first:

```sh
docker compose -f compose.yaml -f compose.app.yaml run --rm migrate
docker compose -f compose.yaml -f compose.app.yaml up -d api worker
pnpm dev
```

Do not start the container API and local API on the same port. Container image builds require network access. No secrets or local snapshots are included in the build context.

When switching an already-populated local catalog to the optional containers, copy its snapshot tree into the shared `snapshots` volume before starting the worker. The database's existing fetch receipts refer to those immutable objects; an empty volume is not a replacement for that history. A fresh container database fills the volume on its first sync.
