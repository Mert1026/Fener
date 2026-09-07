from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fener.config import settings
from fener.models import (
    Deployment,
    IngestionRun,
    MarketEvent,
    Model,
    NotificationCursor,
    Provider,
    Snapshot,
    Source,
    SourceRecord,
    WatchlistItem,
)
from fener.notify import TelegramError
from fener_worker.jobs import notify_watchlist
from pydantic import SecretStr
from sqlalchemy.orm import Session

AUTH = {"Authorization": "Bearer test-admin-key"}


def _seed_evidence(session: Session) -> SourceRecord:
    source = Source(
        id="src-test",
        name="Test source",
        url="https://example.com/feed",
        terms_url="https://example.com/terms",
        attribution="Example",
    )
    run = IngestionRun(id="run-test", source_id="src-test")
    snapshot = Snapshot(
        id="snap-test",
        source_id="src-test",
        content_hash="a" * 64,
        storage_key="aa/test.json",
        url="https://example.com/feed",
        byte_length=64,
    )
    record = SourceRecord(
        id="rec-test",
        source_id="src-test",
        snapshot_id="snap-test",
        external_id="ext-1",
        source_url="https://example.com/feed",
        raw={},
        observed_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    session.add_all([source, run, snapshot, record])
    return record


def _watched_model(session: Session, model_id: str) -> None:
    provider = Provider(id=f"prov-{model_id}", name="Test provider")
    model = Model(
        id=model_id,
        identity_key=f"candidate:src-test:{model_id}",
        name="Test model " + model_id,
        identity_status="resolved",
    )
    deployment = Deployment(
        id=f"dep-{model_id}",
        model_id=model_id,
        access_provider_id=provider.id,
        api_model_id="test/model",
    )
    session.add_all([provider, model, deployment])


def _price_event(session: Session, record_id: str, deployment_id: str, detected_at: datetime):
    event = MarketEvent(
        id=str(uuid4()),
        event_type="price_change",
        entity_type="deployment",
        entity_id=deployment_id,
        title="price input changed",
        old_value={"amount": "2.50"},
        new_value={"amount": "1.75"},
        source_record_id=record_id,
        importance="low",
        detected_at=detected_at,
    )
    session.add(event)
    return event


def _configure_telegram(monkeypatch, sent: list):
    monkeypatch.setattr(settings(), "fener_telegram_bot_token", SecretStr("bot-token"))
    monkeypatch.setattr(settings(), "fener_telegram_chat_id", "chat-1")

    def record_send(token: str, chat_id: str, text: str) -> None:
        sent.append((token, chat_id, text))

    monkeypatch.setattr("fener_worker.jobs.send_telegram_message", record_send)


def test_watchlist_crud_round_trip(client):
    with Session(client.test_engine) as session:
        _watched_model(session, "m-1")
        session.commit()

    response = client.post("/api/v1/watchlist", json={"model_id": "m-1"}, headers=AUTH)
    assert response.status_code == 201
    assert response.json()["model_name"].startswith("Test model")

    duplicate = client.post("/api/v1/watchlist", json={"model_id": "m-1"}, headers=AUTH)
    assert duplicate.status_code == 409

    listing = client.get("/api/v1/watchlist", headers=AUTH)
    assert listing.status_code == 200
    body = listing.json()
    assert body["telegram_configured"] is False
    assert [item["model_id"] for item in body["items"]] == ["m-1"]

    removal = client.delete("/api/v1/watchlist/m-1", headers=AUTH)
    assert removal.status_code == 200
    assert client.get("/api/v1/watchlist", headers=AUTH).json()["items"] == []
    assert client.delete("/api/v1/watchlist/m-1", headers=AUTH).status_code == 404
    assert (
        client.post("/api/v1/watchlist", json={"model_id": "missing"}, headers=AUTH).status_code
        == 404
    )


def test_watchlist_requires_admin(client):
    assert client.get("/api/v1/watchlist").status_code == 401
    assert client.post("/api/v1/watchlist", json={"model_id": "m"}).status_code == 401
    assert client.delete("/api/v1/watchlist/m").status_code == 401


def test_notifications_delivered_for_watched_models(client, monkeypatch):
    sent: list[tuple[str, str, str]] = []
    _configure_telegram(monkeypatch, sent)
    with Session(client.test_engine) as session:
        record = _seed_evidence(session)
        _watched_model(session, "m-1")
        session.add(WatchlistItem(id="watch-1", model_id="m-1"))
        event = _price_event(session, record.id, "dep-m-1", datetime.now(UTC))
        session.commit()

        delivered = notify_watchlist(session, settings())
        assert delivered == 1
        assert len(sent) == 1
        token, chat_id, text = sent[0]
        assert token == "bot-token" and chat_id == "chat-1"
        assert "Test model m-1" in text and "2.50" in text and "1.75" in text
        cursor = session.get(NotificationCursor, "telegram")
        assert cursor is not None and cursor.last_notified_at is not None

        # No new events since the watermark: nothing is redelivered.
        assert notify_watchlist(session, settings()) == 0
        assert len(sent) == 1
        assert event.detected_at is not None


def test_notifications_skip_unwatched_models(client, monkeypatch):
    sent: list[tuple[str, str, str]] = []
    _configure_telegram(monkeypatch, sent)
    with Session(client.test_engine) as session:
        record = _seed_evidence(session)
        _watched_model(session, "m-2")
        _price_event(session, record.id, "dep-m-2", datetime.now(UTC))
        session.commit()
        assert notify_watchlist(session, settings()) == 0
        assert sent == []


def test_notifications_disabled_without_configuration(client, monkeypatch):
    def fail_send(token: str, chat_id: str, text: str) -> None:
        raise TelegramError("must not be called")

    monkeypatch.setattr("fener_worker.jobs.send_telegram_message", fail_send)
    with Session(client.test_engine) as session:
        record = _seed_evidence(session)
        _watched_model(session, "m-3")
        session.add(WatchlistItem(id="watch-3", model_id="m-3"))
        _price_event(session, record.id, "dep-m-3", datetime.now(UTC))
        session.commit()
        assert notify_watchlist(session, settings()) == 0


def test_failed_send_keeps_watermark(client, monkeypatch):
    sent: list[tuple[str, str, str]] = []
    _configure_telegram(monkeypatch, sent)
    with Session(client.test_engine) as session:
        record = _seed_evidence(session)
        _watched_model(session, "m-4")
        session.add(WatchlistItem(id="watch-4", model_id="m-4"))
        _price_event(session, record.id, "dep-m-4", datetime.now(UTC))
        session.commit()

        def failing_send(token: str, chat_id: str, text: str) -> None:
            raise TelegramError("telegram_unreachable")

        monkeypatch.setattr("fener_worker.jobs.send_telegram_message", failing_send)
        try:
            notify_watchlist(session, settings())
        except TelegramError:
            pass
        assert session.get(NotificationCursor, "telegram") is None

        # Recovery: the same events are delivered on the next pass.
        monkeypatch.setattr(
            "fener_worker.jobs.send_telegram_message",
            lambda token, chat_id, text: sent.append((token, chat_id, text)),
        )
        assert notify_watchlist(session, settings()) == 1
        assert len(sent) == 1


def test_market_events_since_filter(client):
    with Session(client.test_engine) as session:
        record = _seed_evidence(session)
        _watched_model(session, "m-5")
        old = _price_event(session, record.id, "dep-m-5", datetime.now(UTC) - timedelta(hours=3))
        recent = _price_event(
            session, record.id, "dep-m-5", datetime.now(UTC) - timedelta(minutes=5)
        )
        session.commit()
        old_id, recent_id = old.id, recent.id

    all_events = client.get("/api/v1/market-events").json()
    assert {row["id"] for row in all_events} >= {old_id, recent_id}
    cutoff = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    filtered = client.get("/api/v1/market-events", params={"since": cutoff}).json()
    assert [row["id"] for row in filtered] == [recent_id]
