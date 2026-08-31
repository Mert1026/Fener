# Operations

## Health and recovery

`GET /healthz` reports process health. `GET /readyz` checks the database migration table. Detailed source status, recent runs, errors and conflicts are available in authenticated Data Health. Worker logs use structured JSON with source and ingestion-run identifiers; credentials are not included. An incomplete or invalid source response preserves raw snapshots and rolls back normalized writes.

Manual source sync requests are persisted by `POST /api/v1/internal/sync` and processed by the worker. Only configured source identifiers are accepted; callers cannot provide arbitrary fetch URLs. Jobs running longer than two hours can be marked interrupted by a subsequent worker. Per-source advisory locks prevent overlapping ingestion; SQLite uses OS-backed file locks. PostgreSQL is required for robust concurrent workers; run only one SQLite worker.

Missing fields are not silently reset to zero or false. They retain their previous observation and become stale without new field confirmation. A model disappearing from a catalog is not automatically proof of global discontinuation. Confirmed availability changes produce events.

## Backup

Back up the database **and** its content-addressed snapshots. Both contain source history; the database can also contain private prompts in evaluation cases and private telemetry.

```sh
python scripts/manage.py backup --docker
```

The Docker option backs up the `db` service in this Compose project. For a different PostgreSQL server, install matching PostgreSQL client tools and omit `--docker`; the script uses `DATABASE_URL` with its password passed through the child environment, not the command line. SQLite uses its online backup API. Output goes to `.data/backups/<timestamp>/`, which is ignored by Git. The manifest identifies whether private data is included. `.env` and secrets are excluded; store keys separately in a password manager.

Backups are not encrypted by this script. Encrypt them before copying to shared storage. Apply your own retention policy; no job deletes historical data automatically. Pause syncs and private writes while making a backup for a strict operational cutoff.

## Restore

1. Stop the API and worker. Keep the original database and snapshot directory intact.
2. Restore into a **new** PostgreSQL database with `pg_restore --no-owner --dbname=<new database> <backup>/fener.dump`. Use client environment variables for authentication. Do not use `--clean` against the live database.
3. Copy the backup's `snapshots` directory to a new local snapshot location. Point `DATABASE_URL` and `FENER_SNAPSHOT_DIR` at the restored resources.
4. Run `uv run alembic current`, `uv run alembic upgrade head`, `uv run alembic check`; inspect model and observation counts and open several evidence records.
5. Restart the API and worker only after verification. Retain the previous database until the restored one is accepted.

For SQLite, restore the backup database under a new filename and update `DATABASE_URL`; use the same snapshot checks. Never delete the active database to perform a restore.

Immediately after a Compose backup, while writes remain paused, run `uv run python scripts/verify_restore.py .data/backups/<timestamp>`. It restores a trusted archive into a uniquely named disposable database, compares every table count with the current live database, verifies backup snapshot hashes, and removes only that test database. If the live database has changed since backup, count differences are expected; they are not by themselves evidence of a corrupt archive. Never use this helper with an untrusted archive.

## Moving the fallback catalog to PostgreSQL

Back up first, apply PostgreSQL migrations to an empty target, and set `DATABASE_URL` to that target. Run `uv run python scripts/transfer_sqlite.py .data/fener.db`. The transfer refuses any target containing catalog or private rows, runs in one PostgreSQL transaction, preserves identifiers and checks every table's row count. Prices are reconstructed from native decimal strings rather than SQLite floating-point storage. The original SQLite file is not changed.

## Export

`python scripts/manage.py export` writes catalog tables as JSONL and models as CSV under `.data/exports`. An explicit table allowlist excludes harnesses, telemetry, policies, evaluation cases/outputs, recommendation requests and manual review notes. Source attribution and evidence references travel with the exported records. CSV cells are protected against spreadsheet formula injection.

Catalog export is not blanket redistribution permission. Review the relevant source's terms in `docs/sources.md` before publishing or redistributing data.
