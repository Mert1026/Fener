from datetime import UTC, datetime, timedelta

import structlog
from fener.config import Settings
from fener.db import utcnow
from fener.private_models import SyncRequest
from fener.sources.ingestion import sync_source
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
