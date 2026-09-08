import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx
import structlog
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from fener.config import Settings
from fener.db import utcnow
from fener.evidence import digest
from fener.models import FetchReceipt, IngestionRun, Snapshot, Source
from fener.sources import litellm, models_dev
from fener.sources.contracts import NormalizedRecord
from fener.sources.persist import CatalogWriter
from fener.sources.registry import RETIRED_SOURCES, SOURCES
from fener.sources.transport import LocalSnapshotStore, fetch

log = structlog.get_logger()


def ensure_sources(session: Session, config: Settings) -> None:
    for retired in session.scalars(select(Source).where(Source.id.in_(RETIRED_SOURCES))):
        retired.enabled = False
        retired.status = "retired"
    for spec in SOURCES.values():
        source = session.get(Source, spec.id)
        if source is None:
            session.add(
                Source(
                    id=spec.id,
                    name=spec.name,
                    url=spec.url,
                    terms_url=spec.terms_url,
                    attribution=spec.attribution,
                    interval_seconds=config.fener_sync_interval_seconds,
                )
            )
        else:
            source.interval_seconds = config.fener_sync_interval_seconds
    session.commit()


@contextmanager
def source_lock(session: Session, source_id: str, config: Settings) -> Iterator[None]:
    engine = session.get_bind()
    if engine.dialect.name == "postgresql":
        lock_id = int(digest("source", source_id)[:15], 16)
        with engine.connect() as connection:  # type: ignore[union-attr]
            if not connection.scalar(text("SELECT pg_try_advisory_lock(:id)"), {"id": lock_id}):
                raise RuntimeError("Source sync already running")
            try:
                yield
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": lock_id})
    else:
        # OS-backed lock releases after a crash; file existence alone is not a lock.
        import filelock

        config.fener_snapshot_dir.mkdir(parents=True, exist_ok=True)
        with filelock.FileLock(config.fener_snapshot_dir / f"{source_id}.lock", timeout=0):
            yield


def sync_source(
    session: Session, source_id: str, config: Settings, client: httpx.Client | None = None
) -> IngestionRun:
    if source_id not in SOURCES:
        raise ValueError("Unknown source")
    ensure_sources(session, config)
    with source_lock(session, source_id, config):
        return _sync(session, source_id, config, client)


def _sync(
    session: Session, source_id: str, config: Settings, client: httpx.Client | None
) -> IngestionRun:
    run = IngestionRun(id=str(uuid4()), source_id=source_id)
    session.add(run)
    session.commit()
    source = session.get(Source, source_id)
    assert source is not None
    own_client = client is None
    client = client or httpx.Client(
        timeout=httpx.Timeout(30, connect=10), headers={"User-Agent": "Fener/0.1 catalog research"}
    )
    store = LocalSnapshotStore(config.fener_snapshot_dir)
    normalized: list[tuple[NormalizedRecord, str, str]] = []

    def load(url: str, normalizer: Callable[[Any], list[NormalizedRecord]]) -> Any:
        headers: dict[str, str] = {}
        last = session.scalar(
            select(FetchReceipt)
            .join(IngestionRun)
            .where(
                FetchReceipt.url == url,
                IngestionRun.source_id == source_id,
                IngestionRun.status == "success",
            )
            .order_by(FetchReceipt.retrieved_at.desc())
        )
        if last:
            if last.etag:
                headers["If-None-Match"] = last.etag
            if last.last_modified:
                headers["If-Modified-Since"] = last.last_modified
        result = fetch(client, url, headers)
        run.http_status = result.status
        if result.status == 304:
            snapshot = session.get(Snapshot, last.snapshot_id) if last else None
            if snapshot is None:
                raise ValueError("304 without a known snapshot")
            content = store.get(snapshot.storage_key)
        else:
            content = result.content
            content_hash, storage_key = store.put(content)
            snapshot_id = digest(source_id, url, content_hash)
            snapshot = session.get(Snapshot, snapshot_id)
            if snapshot is None:
                snapshot = Snapshot(
                    id=snapshot_id,
                    source_id=source_id,
                    content_hash=content_hash,
                    storage_key=storage_key,
                    url=url,
                    byte_length=len(content),
                )
                session.add(snapshot)
                session.flush()
        session.add(
            FetchReceipt(
                id=str(uuid4()),
                run_id=run.id,
                snapshot_id=snapshot.id,
                url=url,
                status=result.status,
                etag=result.etag or (last.etag if last else None),
                last_modified=result.last_modified or (last.last_modified if last else None),
            )
        )
        session.commit()  # Raw evidence survives normalization/validation failure.
        payload = json.loads(content, parse_float=Decimal)
        records = normalizer(payload)
        normalized.extend((row, snapshot.id, url) for row in records)
        return payload

    try:
        if source_id == "models_dev":
            load("https://models.dev/models.json", models_dev.normalize_models)
            load(SOURCES[source_id].url, models_dev.normalize)
        elif source_id == "litellm":
            load(SOURCES[source_id].url, litellm.normalize)
        if not normalized:
            raise ValueError("Source returned an empty catalog; no canonical changes applied")
        writer = CatalogWriter(session, source_id, utcnow())
        # Deterministic order, namespaced (canonical-form) entries first: when
        # several upstream entries resolve to the same deployment, the same one
        # must win on every sync or the values flip-flop between snapshots.
        normalized.sort(
            key=lambda item: (0 if "/" in item[0].external_id else 1, item[0].external_id)
        )
        for row, snapshot_id, url in normalized:
            run.records_changed += int(writer.persist(row, snapshot_id, url))
        run.records_discovered = len(normalized)
        run.status = source.status = "success"
        source.last_success_at = utcnow()
        run.completed_at = utcnow()
        session.commit()
        log.info(
            "sync_completed",
            source_id=source_id,
            ingestion_run_id=run.id,
            discovered=run.records_discovered,
            changed=run.records_changed,
        )
    except Exception as error:
        # Transaction boundary: preserve prior canonical state and record a visible failure.
        session.rollback()
        persisted_run = session.get(IngestionRun, run.id)
        source = session.get(Source, source_id)
        assert persisted_run is not None and source is not None
        run = persisted_run
        run.status = source.status = "failed"
        run.error = f"{type(error).__name__}: source fetch or validation failed; inspect raw snapshot and local logs"
        if isinstance(error, httpx.HTTPStatusError):
            run.http_status = error.response.status_code
        run.completed_at = utcnow()
        session.commit()
        log.error(
            "sync_failed",
            source_id=source_id,
            ingestion_run_id=run.id,
            error_type=type(error).__name__,
        )
        raise
    finally:
        if own_client:
            client.close()
    return run
