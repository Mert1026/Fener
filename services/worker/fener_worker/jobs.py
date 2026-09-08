from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from fener.config import Settings
from fener.db import utcnow
from fener.models import (
    Deployment,
    MarketEvent,
    Model,
    NotificationCursor,
    WatchlistItem,
)
from fener.notify import send_telegram_message
from fener.private_models import SyncRequest
from fener.sources.ingestion import sync_source
from fener.sources.registry import SOURCES
from sqlalchemy import select
from sqlalchemy.orm import Session


def process_queue(session: Session, config: Settings) -> int:
    # A crashed worker must not leave a source permanently queued. Source-level
    # advisory/OS locks still prevent duplicate ingestion after lease recovery.
    expired = datetime.now(UTC) - timedelta(hours=2)
    for stale in session.scalars(
        select(SyncRequest).where(SyncRequest.status == "running", SyncRequest.created_at < expired)
    ):
        stale.status, stale.active_source, stale.completed_at = "interrupted", None, utcnow()
    session.commit()
    for retired in session.scalars(
        select(SyncRequest).where(
            SyncRequest.status == "queued", SyncRequest.source_id.not_in(SOURCES)
        )
    ):
        retired.status, retired.active_source, retired.completed_at = "retired", None, utcnow()
    session.commit()
    row = session.scalar(
        select(SyncRequest)
        .where(SyncRequest.status == "queued")
        .order_by(SyncRequest.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if row is None:
        return 0
    row.status = "running"
    session.commit()
    try:
        run = sync_source(session, row.source_id, config)
        row.ingestion_run_id, row.status = run.id, run.status
    except Exception as error:
        session.rollback()
        row.status = "failed"
        structlog.get_logger().error(
            "queued_sync_failed", source_id=row.source_id, error_type=type(error).__name__
        )
    row.active_source, row.completed_at = None, utcnow()
    session.commit()
    return 1


def _amount(value: Any) -> str:
    if isinstance(value, dict) and "amount" in value:
        return str(value["amount"])
    return str(value)


def notify_watchlist(session: Session, config: Settings) -> int:
    """Deliver price changes on watched models to Telegram.

    One grouped message per pass, at most 20 events; the channel watermark only
    advances after a successful send, so delivery is at-least-once and a
    Telegram outage redelivers on the next worker pass.
    """
    token = config.fener_telegram_bot_token.get_secret_value()
    chat_id = config.fener_telegram_chat_id
    if not token or not chat_id:
        return 0
    cursor = session.get(NotificationCursor, "telegram")
    watermark = cursor.last_notified_at if cursor else None
    query = (
        select(MarketEvent, Deployment, Model)
        .join(
            Deployment,
            (MarketEvent.entity_type == "deployment") & (MarketEvent.entity_id == Deployment.id),
        )
        .join(Model, Deployment.model_id == Model.id)
        .join(WatchlistItem, WatchlistItem.model_id == Model.id)
        .where(MarketEvent.event_type == "price_change")
        .order_by(MarketEvent.detected_at, MarketEvent.id)
        .limit(20)
    )
    if watermark is not None:
        query = query.where(MarketEvent.detected_at > watermark)
    rows = session.execute(query).all()
    if not rows:
        return 0
    lines = [
        f"• {model.name} — {deployment.access_provider_id}: "
        f"{_amount(event.old_value)} → {_amount(event.new_value)}"
        for event, deployment, model in rows
    ]
    text = "Fener price changes on watched models:\n" + "\n".join(lines)
    send_telegram_message(token, chat_id, text)
    latest = max(event.detected_at for event, _, _ in rows)
    if cursor is None:
        cursor = NotificationCursor(channel="telegram", last_notified_at=latest)
        session.add(cursor)
    else:
        cursor.last_notified_at = latest
    session.commit()
    structlog.get_logger().info("watchlist_notified", delivered=len(rows))
    return len(rows)
