"""One-way local SQLite -> empty PostgreSQL transfer; preserves identifiers and history.

Back up first. Apply PostgreSQL migrations, set DATABASE_URL to the target, then run
uv run python scripts/transfer_sqlite.py .data/fener.db. No existing rows are replaced.
"""

import argparse
from decimal import Decimal, localcontext
from pathlib import Path

from fener import models, private_models  # noqa: F401
from fener.db import Base, get_engine, make_engine
from sqlalchemy import func, select


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit("Source database does not exist")
    target = get_engine()
    if target.dialect.name != "postgresql":
        raise SystemExit("DATABASE_URL must point to migrated PostgreSQL")
    source = make_engine(f"sqlite:///{args.source.resolve().as_posix()}")
    with source.connect() as origin, target.begin() as destination:
        for table in Base.metadata.sorted_tables:
            if destination.scalar(select(func.count()).select_from(table)):
                raise SystemExit(f"Target table {table.name} is not empty; transfer refused")
        for table in Base.metadata.sorted_tables:
            copied = 0
            for batch in origin.execute(select(table)).mappings().partitions(500):
                values = [dict(row) for row in batch]
                if table.name == "pricing_observations":
                    for row in values:
                        # SQLite NUMERIC may use binary floats. Reconstruct from
                        # the preserved native decimal string and exact units.
                        with localcontext() as context:
                            context.prec = 100
                            row["amount"] = (
                                Decimal(row["native_amount"])
                                * row["quantity"]
                                / row["native_quantity"]
                            )
                destination.execute(table.insert(), values)
                copied += len(values)
            count = destination.scalar(select(func.count()).select_from(table))
            if count != copied:
                raise RuntimeError(f"Row count mismatch for {table.name}")
            print(f"{table.name}: {copied} rows preserved")
    source.dispose()
    target.dispose()


if __name__ == "__main__":
    main()
