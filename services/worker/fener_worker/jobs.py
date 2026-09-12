from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
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
from fener.value_comparison import equal_prices
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


def _metric_from_title(title: str) -> str:
    key = title.removesuffix(" changed").replace(" ", "_")
    for prefix in ("price.", "price_"):
        if key.startswith(prefix):
            return key[len(prefix) :]
    return key


_METRIC_LABELS = {
    "input": "input",
    "input_tokens": "input",
    "output": "output",
    "output_tokens": "output",
    "cached_input": "cached input",
    "cache_write": "cache write",
    "reasoning": "reasoning",
    "reasoning_tokens": "reasoning",
    "audio_input_tokens": "audio in",
    "audio_output_tokens": "audio out",
}

_METRIC_ORDER = [
    "input",
    "input_tokens",
    "output",
    "output_tokens",
    "cached_input",
    "cache_write",
    "reasoning",
    "reasoning_tokens",
    "audio_input_tokens",
    "audio_output_tokens",
]


def _metric_label(metric: str) -> str:
    return _METRIC_LABELS.get(metric, metric.replace("_", " ").replace(".", " "))


def _format_usd(amount: Decimal) -> str:
    text = format(amount, "f")
    if "." in text:
        whole, frac = text.split(".", 1)
        frac = frac.rstrip("0")
        if len(frac) < 2:
            frac = frac.ljust(2, "0")
        text = f"{whole}.{frac}"
    else:
        text = f"{text}.00"
    return f"${text}"


def _format_price(value: Any) -> str:
    if not isinstance(value, dict) or "amount" not in value:
        return str(value)
    try:
        amount = Decimal(str(value["amount"]))
    except (InvalidOperation, ValueError, TypeError):
        return str(value.get("amount"))
    price = _format_usd(amount)
    unit = value.get("unit", "tokens")
    quantity = value.get("quantity", 1_000_000)
    if unit == "tokens" and quantity == 1_000_000:
        return f"{price}/1M"
    return f"{price} per {quantity} {unit}"


def _price_movement(old_value: Any, new_value: Any) -> str:
    try:
        before = Decimal(str(old_value["amount"]))
        after = Decimal(str(new_value["amount"]))
    except (InvalidOperation, ValueError, TypeError, KeyError, AttributeError):
        return "\u2192"
    if after > before:
        arrow = "\u25b2"
    elif after < before:
        arrow = "\u25bc"
    else:
        return "="
    if before > 0:
        pct = (after - before) / before * 100
        sign = "+" if pct > 0 else ""
        return f"{arrow} {sign}{pct:.1f}%"
    return arrow


def _metric_sort_key(metric: str) -> tuple[int, str]:
    try:
        return (_METRIC_ORDER.index(metric), metric)
    except ValueError:
        return (len(_METRIC_ORDER), metric)


def _move_sort_key(move: tuple[Any, Any, Any, str, Any, Any]) -> tuple[str, str, tuple[int, str]]:
    _, deployment, model, metric, _, _ = move
    return (model.name, deployment.access_provider_id, _metric_sort_key(metric))


def _coalesce_moves(
    rows: list[Any],
) -> tuple[list[tuple[Any, Any, Any, str, Any, Any]], int]:
    # One logical price change emits one MarketEvent per metric (input, output,
    # cache, ...), so collapse to the latest event per (deployment, metric) and
    # drop formatting-only noise (per-1-token vs per-1M views of the same rate).
    latest: dict[tuple[str, str], tuple[Any, Any, Any, str]] = {}
    for event, deployment, model in rows:
        if event.event_type == "price_change" and equal_prices(event.old_value, event.new_value):
            continue
        metric = _metric_from_title(event.title)
        key = (deployment.id, metric)
        current = latest.get(key)
        if current is None or (event.detected_at, event.id) > (
            current[0].detected_at,
            current[0].id,
        ):
            latest[key] = (event, deployment, model, metric)
    kept = [
        (event, deployment, model, metric, event.old_value, event.new_value)
        for event, deployment, model, metric in latest.values()
    ]
    return kept, len(rows) - len(kept)


def notify_watchlist(session: Session, config: Settings) -> int:
    """Deliver price changes on watched models to Telegram.

    One short digest per pass: events are collapsed to the latest change per
    (deployment, price metric), equivalent-price noise is skipped, and each
    deployment gets one line naming the affected metrics. The 20-event fetch
    window and the at-least-once channel watermark are unchanged.
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
    latest = max(event.detected_at for event, _, _ in rows)
    moves, skipped = _coalesce_moves(list(rows))
    if not moves:
        # Only noise was found: advance past it so it is not re-scanned, and
        # stay silent instead of sending a confusing empty digest.
        if cursor is None:
            cursor = NotificationCursor(channel="telegram", last_notified_at=latest)
            session.add(cursor)
        else:
            cursor.last_notified_at = latest
        session.commit()
        return 0
    # One line per deployment: "Model via provider: input $x→$y (▼ -30%), output ...".
    by_deployment: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for _event, deployment, model, metric, old_value, new_value in sorted(
        moves, key=_move_sort_key
    ):
        entry = by_deployment.get(deployment.id)
        if entry is None:
            entry = {"model": model, "deployment": deployment, "parts": []}
            by_deployment[deployment.id] = entry
            order.append(deployment.id)
        movement = _price_movement(old_value, new_value)
        entry["parts"].append(
            f"{_metric_label(metric)} {_format_price(old_value)}\u2192{_format_price(new_value)} ({movement})"
        )
    lines = [
        f"\U0001f4b0 {by_deployment[deployment_id]['model'].name} via "
        f"{by_deployment[deployment_id]['deployment'].access_provider_id}: "
        + "; ".join(by_deployment[deployment_id]["parts"])
        for deployment_id in order
    ]
    skipped_note = f" (+{skipped} duplicate/no-op update(s) hidden)" if skipped else ""
    text = "Price update on your watchlist" + skipped_note + ":\n" + "\n".join(lines)
    send_telegram_message(token, chat_id, text)
    if cursor is None:
        cursor = NotificationCursor(channel="telegram", last_notified_at=latest)
        session.add(cursor)
    else:
        cursor.last_notified_at = latest
    session.commit()
    structlog.get_logger().info("watchlist_notified", delivered=len(moves), skipped=skipped)
    return len(moves)
