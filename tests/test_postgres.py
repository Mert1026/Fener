"""Real PostgreSQL migration/precision check, using an isolated temporary schema."""

import os
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fener.db import make_engine
from fener.models import Price, Snapshot, Source
from fener.sources.contracts import NativePrice, NormalizedRecord
from fener.sources.persist import CatalogWriter
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


@pytest.mark.skipif(
    not os.getenv("FENER_TEST_POSTGRES_URL"), reason="PostgreSQL integration URL not configured"
)
def test_postgres_migrations_idempotence_and_exact_money():
    url = make_url(os.environ["FENER_TEST_POSTGRES_URL"])
    assert url.get_backend_name() == "postgresql"
    schema = "fener_test_" + uuid4().hex
    engine = make_engine(url.render_as_string(hide_password=False))
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = url.set(query={**url.query, "options": f"-csearch_path={schema}"})
    scoped = make_engine(scoped_url.render_as_string(hide_password=False))
    try:
        environment = {
            **os.environ,
            "DATABASE_URL": scoped_url.render_as_string(hide_password=False),
        }
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"], env=environment, check=True
        )
        subprocess.run([sys.executable, "-m", "alembic", "check"], env=environment, check=True)
        with Session(scoped) as session:
            session.add(
                Source(
                    id="models_dev",
                    name="Fixture",
                    url="https://models.dev",
                    terms_url="https://models.dev",
                    attribution="Fixture only",
                )
            )
            session.flush()
            session.add(
                Snapshot(
                    id="fixture",
                    source_id="models_dev",
                    content_hash="fixture",
                    storage_key="fixture.json",
                    url="https://models.dev",
                    byte_length=2,
                )
            )
            session.commit()
            amount = Decimal("0.049999999999999996")
            row = NormalizedRecord(
                external_id="fixture/model",
                canonical_id="fixture/model",
                canonical=True,
                name="Fixture",
                provider_id="fixture",
                api_id="model",
                raw={"price": str(amount)},
                prices=[NativePrice(metric="input_tokens", amount=amount, quantity=1000000)],
            )
            for _ in range(2):
                CatalogWriter(session, "models_dev", datetime.now(UTC)).persist(
                    row, "fixture", "https://models.dev"
                )
                session.commit()
            assert session.scalar(select(func.count()).select_from(Price)) == 1
            assert session.scalar(select(Price.amount)) == amount
    finally:
        scoped.dispose()
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
