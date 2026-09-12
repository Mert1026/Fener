from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fener.maintenance import purge_concurrent_conflict_artifacts
from fener.models import Fact, MarketEvent, Price, Snapshot, Source
from fener.sources.contracts import NativePrice, NormalizedRecord
from fener.sources.persist import CatalogWriter
from sqlalchemy import func, select


def setup_source(session, source_id="litellm"):
    session.add(
        Source(
            id=source_id,
            name=source_id,
            url="https://example.com",
            terms_url="https://example.com",
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
            url="https://example.com",
            byte_length=1,
        )
    )
    session.commit()


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


def _sync_writer(session, tick):
    return CatalogWriter(
        session, "litellm", datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=tick)
    )


def test_purge_removes_flip_flop_artifacts_and_keeps_tip(session):
    setup_source(session)
    prefixed = gemini_entry("gemini/gemini-exp-1206", "0", 2097152)
    bare = gemini_entry("gemini-exp-1206", "2.5", 1048576)

    # Pre-fix behavior: both entries wrote at the same instant.
    _sync_writer(session, 0).persist(prefixed, "litellm", "https://example.com")
    _sync_writer(session, 0).persist(bare, "litellm", "https://example.com")
    # A later, legitimate single-entry observation.
    _sync_writer(session, 6).persist(prefixed, "litellm", "https://example.com")
    session.commit()

    assert session.scalar(select(func.count()).select_from(Fact)) > 2
    deleted = purge_concurrent_conflict_artifacts(session.connection())
    session.commit()
    assert deleted > 0

    # Only the tip of each conflicted chain survives; the legitimate later
    # observation and its event stay.
    price_facts = session.scalars(select(Fact).where(Fact.field == "price.output_tokens")).all()
    assert len(price_facts) == 1
    assert price_facts[0].value["amount"] == "0"
    flip_events = session.scalars(
        select(MarketEvent).where(MarketEvent.detected_at == datetime(2026, 1, 1, tzinfo=UTC))
    ).all()
    assert flip_events == []
    prices = session.scalars(select(Price)).all()
    assert len(prices) == 1
    assert prices[0].amount == Decimal("0")

    # Idempotent: a second pass removes nothing.
    assert purge_concurrent_conflict_artifacts(session.connection()) == 0
