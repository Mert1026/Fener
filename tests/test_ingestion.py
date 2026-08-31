import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from fener.catalog import facts_for
from fener.config import Settings
from fener.models import (
    Conflict,
    CurrentFact,
    Fact,
    IngestionRun,
    Model,
    Price,
    Snapshot,
    Source,
    SourceRecord,
)
from fener.sources.contracts import NativePrice, NormalizedRecord
from fener.sources.ingestion import sync_source
from fener.sources.persist import CatalogWriter
from sqlalchemy import func, select


def setup_source(session, source_id="models_dev"):
    session.add(
        Source(
            id=source_id,
            name=source_id,
            url="https://models.dev/api.json",
            terms_url="https://models.dev",
            attribution="test",
        )
    )
    session.flush()
    session.add(
        Snapshot(
            id=source_id,
            source_id=source_id,
            content_hash="x",
            storage_key="test.json",
            url="https://models.dev/api.json",
            byte_length=1,
        )
    )
    session.commit()


def row(amount="1", canonical=False):
    return NormalizedRecord(
        external_id="test/model",
        name="Fixture model",
        canonical_id="test/model",
        canonical=canonical,
        publisher_id="test",
        provider_id="test",
        provider_name="Test",
        api_id="model",
        deployment_facts={"tool_calling": True},
        prices=[NativePrice(metric="input_tokens", amount=amount, quantity=1000000)],
        raw={"price": amount},
    )


def write(session, amount, source="models_dev", tick=0):
    writer = CatalogWriter(
        session, source, datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=tick)
    )
    writer.persist(
        row(amount, canonical=source == "models_dev"), source, "https://models.dev/api.json"
    )
    session.commit()


def test_idempotence_and_price_reversion(session):
    setup_source(session)
    write(session, "1")
    write(session, "1", tick=1)
    assert session.scalar(select(func.count()).select_from(Price)) == 1
    write(session, "2", tick=2)
    write(session, "1", tick=3)
    assert session.scalar(select(func.count()).select_from(Price)) == 3
    current = session.scalar(
        select(Fact)
        .join(CurrentFact, CurrentFact.observation_id == Fact.id)
        .where(Fact.field == "price.input_tokens")
    )
    assert current.value["amount"] == "1"
    assert session.scalar(select(func.count()).select_from(SourceRecord)) == 2


def test_conflicting_sources_do_not_destroy_history(session):
    setup_source(session)
    setup_source(session, "litellm")
    write(session, "1")
    write(session, "2", "litellm", 1)
    conflict = session.scalar(select(Conflict).where(Conflict.field == "price.input_tokens"))
    assert conflict is not None
    assert conflict.status == "automatically_resolved"
    current = session.scalar(
        select(Fact)
        .join(CurrentFact, CurrentFact.observation_id == Fact.id)
        .where(Fact.field == "price.input_tokens")
    )
    assert current.value["amount"] == "1"


def test_invalid_source_keeps_raw_snapshot_and_no_models(session, tmp_path):
    config = Settings(fener_snapshot_dir=tmp_path)
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"broken": True}))
    )
    with pytest.raises(ValueError):
        sync_source(session, "models_dev", config, client)
    assert session.scalar(select(func.count()).select_from(Model)) == 0
    assert session.scalar(select(func.count()).select_from(Snapshot)) == 1
    assert session.scalar(select(IngestionRun)).status == "failed"


def test_missing_key_is_explicit_and_no_network(session, tmp_path):
    def reject(_):
        pytest.fail("Missing key must not cause network requests")

    run = sync_source(
        session,
        "llm_stats",
        Settings(fener_snapshot_dir=tmp_path, llm_stats_api_key=""),
        httpx.Client(transport=httpx.MockTransport(reject)),
    )
    assert run.status == "needs_key"


def test_decimal_json_keeps_source_precision():
    value = json.loads('{"price": 0.049999999999999996}', parse_float=Decimal)
    price = NativePrice(metric="input_tokens", amount=value["price"], quantity=1000000)
    assert price.normalized == Decimal("0.049999999999999996")


def test_unchanged_price_retains_confirmation_with_changed_raw_metadata(session):
    setup_source(session)
    write(session, "1")
    original = session.scalar(select(Price))
    later = datetime(2026, 1, 2, tzinfo=UTC)
    record = row("1", canonical=True)
    record.raw["description"] = "Source changed unrelated metadata"
    CatalogWriter(session, "models_dev", later).persist(
        record, "models_dev", "https://models.dev/api.json"
    )
    session.commit()
    assert session.scalar(select(func.count()).select_from(Price)) == 1
    fact = facts_for(session, "deployment", [original.deployment_id])[original.deployment_id][
        "price.input_tokens"
    ]
    assert fact.last_seen_at == later
    assert fact.id == original.id
