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
    MarketEvent,
    Model,
    Price,
    Snapshot,
    Source,
    SourceRecord,
)
from fener.sources.contracts import NativePrice, NormalizedRecord
from fener.sources.ingestion import ensure_sources, sync_source
from fener.sources.persist import CatalogWriter
from sqlalchemy import func, select
from sqlalchemy.orm import Session


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


def gemini_entry(external_id: str, amount: str, max_input: int) -> NormalizedRecord:
    """The real LiteLLM shape: bare and namespaced keys for one Gemini model."""
    return NormalizedRecord(
        external_id=external_id,
        name="gemini-exp-1206",
        canonical_id="gemini/gemini-exp-1206",
        provider_id="gemini",
        provider_name="gemini",
        api_id="gemini-exp-1206",
        deployment_facts={"max_input": max_input},
        prices=[NativePrice(metric="output_tokens", amount=amount, quantity=1)],
        raw={},
    )


def test_duplicate_entries_within_one_sync_do_not_flip_flop(session):
    """LiteLLM lists `gemini-exp-1206` and `gemini/gemini-exp-1206`; both
    resolve to one deployment. The namespaced entry must win deterministically
    and the conflicting entry must not emit alternating change events."""
    setup_source(session, "litellm")
    prefixed = gemini_entry("gemini/gemini-exp-1206", "0", 2097152)
    bare = gemini_entry("gemini-exp-1206", "2.5", 1048576)

    writer = CatalogWriter(session, "litellm", datetime(2026, 1, 1, tzinfo=UTC))
    for record in (prefixed, bare):
        writer.persist(record, "litellm", "https://example.com")
    session.commit()

    prices = session.scalars(select(Price)).all()
    assert len(prices) == 1
    assert prices[0].amount == Decimal("0")
    facts = session.scalars(select(Fact).where(Fact.field == "max_input")).all()
    assert len(facts) == 1
    assert facts[0].value == 2097152
    # Discovery events only: one new_model, one new_deployment.
    first_sync_events = session.scalar(select(func.count()).select_from(MarketEvent))
    assert first_sync_events == 2

    # A later sync with the same two entries: stable, no new observations.
    later = CatalogWriter(session, "litellm", datetime(2026, 1, 1, 6, tzinfo=UTC))
    for record in (prefixed, bare):
        later.persist(record, "litellm", "https://example.com")
    session.commit()

    assert session.scalar(select(func.count()).select_from(Price)) == 1
    assert (
        session.scalar(select(func.count()).select_from(Fact).where(Fact.field == "max_input")) == 1
    )
    assert session.scalar(select(func.count()).select_from(MarketEvent)) == first_sync_events


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


def test_removed_sources_are_never_fetchable_and_history_is_retired(session, tmp_path):
    setup_source(session, "openrouter")
    with pytest.raises(ValueError, match="Unknown source"):
        sync_source(session, "openrouter", Settings(fener_snapshot_dir=tmp_path))
    ensure_sources(session, Settings())
    retired = session.get(Source, "openrouter")
    assert retired.enabled is False and retired.status == "retired"


def test_schedule_configuration_updates_existing_sources(session):
    ensure_sources(session, Settings(fener_sync_interval_seconds=7200))
    ensure_sources(session, Settings(fener_sync_interval_seconds=14400))
    assert session.get(Source, "models_dev").interval_seconds == 14400


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


def test_decimal_formatting_does_not_create_price_facts_events_or_conflicts(session):
    setup_source(session)
    write(session, "0.2")
    count = session.scalar(select(func.count()).select_from(Fact))
    write(session, "0.2000000", tick=1)
    assert session.scalar(select(func.count()).select_from(Fact)) == count
    assert session.scalar(select(func.count()).select_from(Price)) == 1
    assert session.scalar(select(func.count()).select_from(SourceRecord)) == 2
    assert (
        session.scalar(
            select(func.count())
            .select_from(MarketEvent)
            .where(MarketEvent.event_type == "price_change")
        )
        == 0
    )
    setup_source(session, "litellm")
    write(session, "0.2000", "litellm", 2)
    assert (
        session.scalar(
            select(func.count()).select_from(Conflict).where(Conflict.field == "price.input_tokens")
        )
        == 0
    )
    write(session, "0.200000001", tick=3)
    assert (
        session.scalar(
            select(func.count())
            .select_from(MarketEvent)
            .where(MarketEvent.event_type == "price_change")
        )
        == 1
    )


def test_exact_identity_evidence_promotes_existing_candidate_in_place(session):
    setup_source(session, "litellm")
    candidate = row("1")
    candidate.publisher_id = None
    CatalogWriter(session, "litellm", datetime(2026, 1, 1, tzinfo=UTC)).persist(
        candidate, "litellm", "https://example.test/catalog.json"
    )
    session.commit()
    original = session.scalar(select(Model))
    original_id = original.id

    resolved = row("1", canonical=True)
    CatalogWriter(session, "litellm", datetime(2026, 1, 2, tzinfo=UTC)).persist(
        resolved, "litellm", "https://example.test/catalog.json"
    )
    session.commit()

    promoted = session.get(Model, original_id)
    assert promoted is not None
    assert promoted.identity_key == "canonical:test/model"
    assert promoted.identity_status == "resolved"
    assert promoted.publisher_id == "test"
    assert session.scalar(select(func.count()).select_from(Model)) == 1


def test_market_hides_legacy_formatting_events_before_pagination(client):
    with Session(client.test_engine) as session:
        setup_source(session)
        write(session, "0.2")
        price = session.scalar(select(Price))
        for i, (before, after) in enumerate(
            [("0.2", "0.2000000"), ("0.3", "0.300"), ("0.2", "0.4"), ("0.4", "0.1")]
        ):
            value = {"currency": "USD", "quantity": 1000000, "unit": "tokens"}
            session.add(
                MarketEvent(
                    id=f"legacy-{i}",
                    entity_type="deployment",
                    entity_id=price.deployment_id,
                    event_type="price_change",
                    title="price.input tokens changed",
                    old_value={**value, "amount": before},
                    new_value={**value, "amount": after},
                    source_record_id=price.source_record_id,
                    detected_at=datetime(2026, 1, 2, tzinfo=UTC) - timedelta(hours=i),
                )
            )
        session.commit()
    first = client.get("/api/v1/market-events?event_type=price_change&limit=1").json()
    second = client.get("/api/v1/market-events?event_type=price_change&limit=1&offset=1").json()
    assert [r["id"] for r in first + second] == ["legacy-2", "legacy-3"]
    assert first[0]["change_field"] == "price.input_tokens"
    assert first[0]["model_name"] == "Fixture model"
    with Session(client.test_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(MarketEvent)
                .where(MarketEvent.event_type == "price_change")
            )
            == 4
        )
