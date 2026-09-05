"""Process one durable, non-retried benchmark-research item per worker pass."""

from datetime import timedelta
from urllib.parse import urlsplit

import httpx
from fener.ai_benchmarks import persist_research_benchmarks
from fener.config import Settings
from fener.db import utcnow
from fener.models import Model
from fener.private_models import BenchmarkRefresh, BenchmarkRefreshItem
from fener.zai_research import fetch_zai_research
from sqlalchemy import select
from sqlalchemy.orm import Session

PRIMARY_BENCHMARK = "Artificial Analysis Intelligence Index"
PRIMARY_BENCHMARK_METRIC = "index points"
PRIMARY_EVALUATOR = "Artificial Analysis"
PRIMARY_SOURCE_DOMAIN = "artificialanalysis.ai"


def primary_benchmark_candidate(candidate: dict[str, object]) -> bool:
    try:
        host = (urlsplit(str(candidate["source_url"])).hostname or "").lower()
        return (
            (host == PRIMARY_SOURCE_DOMAIN or host.endswith("." + PRIMARY_SOURCE_DOMAIN))
            and str(candidate["name"]).casefold().strip() == PRIMARY_BENCHMARK.casefold()
            and str(candidate["metric"]).casefold().strip() == PRIMARY_BENCHMARK_METRIC.casefold()
            and str(candidate["evaluator"]).casefold().strip() == PRIMARY_EVALUATOR.casefold()
        )
    except (KeyError, TypeError, ValueError):
        return False


def process_benchmark_refresh(session: Session, config: Settings) -> int:
    job = session.scalar(
        select(BenchmarkRefresh)
        .where(BenchmarkRefresh.status.in_(["queued", "running", "blocked"]))
        .order_by(BenchmarkRefresh.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job is None:
        return 0

    # A provider call may have completed before a crash. Only mark old work as
    # uncertain: a second worker can see a healthy request while it is in flight.
    stale_before = utcnow() - timedelta(minutes=5)
    for stale in session.scalars(
        select(BenchmarkRefreshItem).where(
            BenchmarkRefreshItem.refresh_id == job.id,
            BenchmarkRefreshItem.status == "running",
            BenchmarkRefreshItem.started_at < stale_before,
        )
    ):
        stale.status = "uncertain"
        stale.error = "The worker stopped during this model; no automatic retry was made."
        stale.completed_at = utcnow()
        job.processed_models += 1
        job.failed_models += 1

    # The job row lock and this check keep a catalog refresh sequential even if
    # two worker processes are running.
    running_item = session.scalar(
        select(BenchmarkRefreshItem.id)
        .where(
            BenchmarkRefreshItem.refresh_id == job.id,
            BenchmarkRefreshItem.status == "running",
        )
        .limit(1)
    )
    if running_item:
        session.commit()
        return 0

    key = config.zai_api_key.get_secret_value()
    if not key:
        job.status = "blocked"
        job.error = "ZAI_API_KEY is no longer configured. Restart after restoring the key."
        session.commit()
        return 0

    item = session.scalar(
        select(BenchmarkRefreshItem)
        .where(
            BenchmarkRefreshItem.refresh_id == job.id,
            BenchmarkRefreshItem.status == "queued",
        )
        .order_by(BenchmarkRefreshItem.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if item is None:
        job.status = "completed_with_errors" if job.failed_models else "completed"
        job.completed_at = utcnow()
        session.commit()
        return 0
    model = session.get(Model, item.model_id)
    if model is None:
        item.status, item.error, item.completed_at = (
            "failed",
            "Catalog model no longer exists.",
            utcnow(),
        )
        job.processed_models += 1
        job.failed_models += 1
        session.commit()
        return 1

    job.status = "running"
    job.error = None
    item.status = "running"
    item.started_at = utcnow()
    session.commit()
    request = {
        "model": job.model,
        "query": (
            f"Find the current model-level {PRIMARY_BENCHMARK} result for the exact AI model "
            f"named {model.name!r}. Search only Artificial Analysis model benchmark pages. "
            "Do not use the Coding Agent Index or assign an agent/harness score to a model. "
            f"Return only {PRIMARY_BENCHMARK!r}, use metric {PRIMARY_BENCHMARK_METRIC!r} and "
            f"evaluator {PRIMARY_EVALUATOR!r}, and preserve the published index version, numeric "
            "score, report date, scale and source URL. Return no benchmark candidate unless the "
            "source excerpt explicitly associates this exact model with the score."
        ),
        "search_domain_filter": PRIMARY_SOURCE_DOMAIN,
        "max_output_tokens": 2000,
    }
    try:
        report = fetch_zai_research(request, key)
        candidates = [
            candidate
            for candidate in report.get("benchmark_candidates", [])
            if candidate["model_name"].casefold().strip() == model.name.casefold().strip()
            and primary_benchmark_candidate(candidate)
        ]
        imported = persist_research_benchmarks(session, candidates, refresh_item_id=item.id)[
            "imported"
        ]
        item.status = "success" if imported else "no_evidence"
        if not imported:
            item.error = "Research completed, but no complete cited benchmark claim was found."
        item.imported_results = imported
        job.imported_results += imported
    except httpx.HTTPError:
        item.status = "uncertain"
        item.error = "Provider connection failed or timed out; no automatic retry was made."
        job.failed_models += 1
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        item.status = "failed"
        item.error = f"Research validation failed: {error}"
        job.failed_models += 1
    item.completed_at = utcnow()
    job.processed_models += 1
    session.commit()
    return 1
