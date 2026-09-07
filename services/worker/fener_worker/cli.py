import time
from datetime import UTC, datetime

import structlog
import typer
from fener.config import settings
from fener.db import get_engine
from fener.models import IngestionRun, Source
from fener.sources.ingestion import ensure_sources, sync_source
from fener.sources.registry import SOURCES
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fener_worker.benchmark_jobs import process_benchmark_refresh
from fener_worker.jobs import notify_watchlist, process_queue

app = typer.Typer(help="Fener ingestion and local administration", no_args_is_help=True)


@app.callback()
def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )


@app.command()
def version() -> None:
    """Show the local platform version."""
    typer.echo("Fener 0.1.0")


@app.command()
def sync(source: str | None = None) -> None:
    """Sync one source or all sources, independently. Never invokes inference APIs."""
    if source and source not in SOURCES:
        raise typer.BadParameter(f"Choose: {', '.join(SOURCES)}")
    failures = []
    for source_id in [source] if source else SOURCES:
        try:
            with Session(get_engine()) as session:
                run = sync_source(session, source_id, settings())
                typer.echo(
                    f"{source_id}: {run.status} ({run.records_discovered} records; {run.records_changed} changed)"
                )
                if run.status != "success":
                    failures.append(source_id)
        except Exception as error:
            typer.echo(f"{source_id}: {type(error).__name__}: {error}", err=True)
            failures.append(source_id)
    if failures:
        raise typer.Exit(1)


@app.command()
def worker() -> None:
    """Poll configured per-source schedules; database/OS locks prevent overlapping jobs."""
    structlog.get_logger().info("worker_started", poll_interval_seconds=60)
    while True:
        with Session(get_engine()) as session:
            ensure_sources(session, settings())
            process_queue(session, settings())
            try:
                benchmark_work = process_benchmark_refresh(session, settings())
            except Exception as error:
                session.rollback()
                benchmark_work = 0
                structlog.get_logger().error(
                    "benchmark_refresh_failed", error_type=type(error).__name__
                )
            try:
                notify_watchlist(session, settings())
            except Exception as error:
                session.rollback()
                structlog.get_logger().error(
                    "watchlist_notify_failed", error_type=type(error).__name__
                )
            for source in session.scalars(
                select(Source).where(Source.enabled.is_(True), Source.id.in_(SOURCES))
            ):
                last = session.scalar(
                    select(func.max(IngestionRun.started_at)).where(
                        IngestionRun.source_id == source.id
                    )
                )
                if (
                    last
                    and (datetime.now(UTC) - last.replace(tzinfo=UTC)).total_seconds()
                    < source.interval_seconds
                ):
                    continue
                try:
                    sync_source(session, source.id, settings())
                except Exception as error:
                    structlog.get_logger().error(
                        "scheduled_sync_failed",
                        source_id=source.id,
                        error_type=type(error).__name__,
                    )
        time.sleep(2 if benchmark_work else 60)
