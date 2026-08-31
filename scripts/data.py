"""Local catalog export and backup. Private content never enters catalog exports."""

import argparse
import csv
import json
import os
import shutil
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from fener.config import settings
from fener.db import get_engine
from fener.evidence import json_value
from fener.models import CurrentFact, Deployment, Fact, Model, Provider, Source, SourceRecord
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["backup", "export"])
    parser.add_argument(
        "--docker", action="store_true", help="Back up the Compose db service using its pg_dump"
    )
    args = parser.parse_args()
    config = settings()
    destination = (
        Path(".data")
        / ("backups" if args.command == "backup" else "exports")
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    )
    destination.mkdir(parents=True, exist_ok=False)
    if args.command == "backup":
        url = make_url(config.database_url)
        if url.get_backend_name() == "sqlite":
            with sqlite3.connect(url.database or ".data/fener.db") as source:
                with sqlite3.connect(destination / "fener.db") as target:
                    source.backup(target)
        elif args.docker:
            with (destination / "fener.dump").open("wb") as output:
                subprocess.run(
                    [
                        "docker",
                        "compose",
                        "exec",
                        "-T",
                        "db",
                        "pg_dump",
                        "-U",
                        "fener",
                        "-d",
                        "fener",
                        "--format=custom",
                    ],
                    stdout=output,
                    check=True,
                )
        else:
            pg_dump = shutil.which("pg_dump")
            if not pg_dump:
                raise SystemExit(
                    "Install PostgreSQL client tools (pg_dump), or follow the Docker backup command in docs/operations.md."
                )
            env = {**os.environ, "PGPASSWORD": url.password or ""}
            subprocess.run(
                [
                    pg_dump,
                    "--format=custom",
                    "--host",
                    url.host or "localhost",
                    "--port",
                    str(url.port or 5432),
                    "--username",
                    url.username or "fener",
                    "--dbname",
                    url.database or "fener",
                    "--file",
                    str(destination / "fener.dump"),
                ],
                env=env,
                check=True,
            )
        if config.fener_snapshot_dir.exists():
            shutil.copytree(
                config.fener_snapshot_dir,
                destination / "snapshots",
                ignore=shutil.ignore_patterns("*.lock", "tmp*"),
            )
        (destination / "manifest.json").write_text(
            json.dumps(
                {
                    "created_at": datetime.now(UTC).isoformat(),
                    "database": url.get_backend_name(),
                    "contains_private_data": True,
                    "secrets_included": False,
                }
            ),
            encoding="utf-8",
        )
    else:
        # Explicit table allowlist is the boundary: no harnesses, telemetry, prompts,
        # evaluations, policies, recommendations or manual review notes are exported.
        with Session(get_engine()) as session:
            for table in [Model, Provider, Deployment, Source, Fact, CurrentFact, SourceRecord]:
                columns = [column.name for column in table.__table__.columns]
                rows = (
                    json_value({key: getattr(row, key) for key in columns})
                    for row in session.scalars(select(table))
                )
                with (destination / f"{table.__tablename__}.jsonl").open(
                    "w", encoding="utf-8"
                ) as file:
                    for row in rows:
                        file.write(json.dumps(row, ensure_ascii=False) + "\n")
            with (destination / "models.csv").open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["id", "name", "publisher", "identity_status"])
                for row in session.scalars(select(Model)):
                    # Prevent spreadsheet formula execution from upstream text.
                    values = [row.id, row.name, row.publisher_id or "", row.identity_status]
                    writer.writerow(
                        [
                            "'" + v if v.startswith(("=", "+", "-", "@", "\t", "\r")) else v
                            for v in values
                        ]
                    )
    print(f"Created {destination.resolve()}")


if __name__ == "__main__":
    main()
