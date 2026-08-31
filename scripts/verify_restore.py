"""Verify a trusted local Compose backup in a disposable PostgreSQL database.

Never use untrusted archives. The live database is only read; the generated test
database is removed in finally. Requires the local Compose db service and Docker.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from uuid import uuid4

import psycopg
from fener import models, private_models  # noqa: F401
from fener.db import Base, get_engine, make_engine
from fener.sources.transport import LocalSnapshotStore
from psycopg import sql
from sqlalchemy import func, select


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    backup = args.backup.resolve()
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    if manifest["database"] != "postgresql" or not (backup / "fener.dump").is_file():
        raise SystemExit("Expected a PostgreSQL backup directory")
    live = get_engine()
    url = live.url
    if live.dialect.name != "postgresql" or url.host not in {"localhost", "127.0.0.1"}:
        raise SystemExit("This check is limited to local Compose PostgreSQL")
    name = "fener_restore_check_" + uuid4().hex
    admin_url = url.set(drivername="postgresql").render_as_string(hide_password=False)
    restored = make_engine(url.set(database=name).render_as_string(hide_password=False))
    created = False
    with psycopg.connect(admin_url, autocommit=True) as admin:
        try:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            created = True
            with (backup / "fener.dump").open("rb") as archive:
                subprocess.run(
                    [
                        "docker",
                        "compose",
                        "exec",
                        "-T",
                        "db",
                        "pg_restore",
                        "--exit-on-error",
                        "--no-owner",
                        "--username",
                        "fener",
                        "--dbname",
                        name,
                    ],
                    stdin=archive,
                    check=True,
                )
            with live.connect() as current, restored.connect() as recovered:
                for table in Base.metadata.sorted_tables:
                    # Run this directly after backup, before resuming writes.
                    assert current.scalar(
                        select(func.count()).select_from(table)
                    ) == recovered.scalar(select(func.count()).select_from(table)), table.name
                store = LocalSnapshotStore(backup / "snapshots")
                for row in recovered.execute(select(models.Snapshot.__table__)).mappings():
                    assert (
                        hashlib.sha256(store.get(row["storage_key"])).hexdigest()
                        == row["content_hash"]
                    )
            print(
                "Restored every table; row counts and backup snapshot hashes match. Live database unchanged."
            )
        finally:
            restored.dispose()
            if created:
                admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


if __name__ == "__main__":
    main()
