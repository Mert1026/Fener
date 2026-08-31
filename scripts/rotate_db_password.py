"""Rotate the configured loopback PostgreSQL role password, preserving its data.

Stop Fener app/worker processes and back up first. Run from the repository root
with uv run python scripts/rotate_db_password.py. Never prints credentials.
"""

import os
import re
import secrets
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql
from sqlalchemy.engine import make_url


def main():
    path = Path(".env")
    original = path.read_text(encoding="utf-8")
    values = dotenv_values(path)
    url = make_url(values.get("DATABASE_URL") or "")
    if url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("This command only rotates the local loopback PostgreSQL database.")
    if not url.username:
        raise SystemExit("DATABASE_URL must specify the local database role.")
    password = secrets.token_hex(32)
    updated = original
    for key, value in {
        "DATABASE_URL": url.set(password=password).render_as_string(hide_password=False),
        "POSTGRES_PASSWORD": password,
    }.items():
        pattern = rf"(?m)^{key}=.*$"
        updated = (
            re.sub(pattern, lambda _, key=key, value=value: f"{key}={value}", updated)
            if re.search(pattern, updated)
            else updated + f"\n{key}={value}\n"
        )
    # Keep recovery material in the existing ignored .env path, never stdout.
    connection = psycopg.connect(
        host=url.host,
        port=url.port or 5432,
        dbname=url.database,
        user=url.username,
        password=url.password,
        connect_timeout=10,
    )
    try:
        with connection:
            connection.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(url.username), sql.Literal(password)
                )
            )
            path.write_text(updated, encoding="utf-8")
            if os.name != "nt":
                path.chmod(0o600)
    except Exception:
        path.write_text(original, encoding="utf-8")
        raise SystemExit(
            "Rotation failed; the original .env was restored. Verify local database connectivity before retrying."
        ) from None
    with psycopg.connect(
        host=url.host,
        port=url.port or 5432,
        dbname=url.database,
        user=url.username,
        password=password,
        connect_timeout=10,
    ) as verified:
        verified.execute("SELECT 1")
    print(
        "Local database credential rotated and verified. Existing data and other .env settings were preserved. Restart Fener services."
    )


if __name__ == "__main__":
    main()
