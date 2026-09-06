"""Refresh one comparable benchmark cohort from Artificial Analysis."""

import re
from collections import defaultdict

import httpx
from fener.ai_benchmarks import persist_research_benchmarks
from fener.artificial_analysis import IntelligenceIndexResult, fetch_current_intelligence_index
from fener.config import Settings
from fener.db import utcnow
from fener.models import Model
from fener.private_models import BenchmarkRefresh, BenchmarkRefreshItem
from sqlalchemy import select
from sqlalchemy.orm import Session

PRIMARY_BENCHMARK = "Artificial Analysis Intelligence Index"
PRIMARY_BENCHMARK_METRIC = "index points"
PRIMARY_EVALUATOR = "Artificial Analysis"
DATED_MODEL_SUFFIX = re.compile(r"[-_]20\d{2}[-_]\d{2}[-_]\d{2}$")


def comparable_name(value: str) -> str:
    value = DATED_MODEL_SUFFIX.sub("", value.casefold().strip())
    return re.sub(r"[^a-z0-9]+", "", value)


def match_current_result(
    model_name: str, rows: list[IntelligenceIndexResult]
) -> IntelligenceIndexResult | None:
    key = comparable_name(model_name)
    matches = {row for row in rows if key in {comparable_name(row.slug), comparable_name(row.name)}}
    return next(iter(matches)) if len(matches) == 1 else None


def benchmark_candidate(model: Model, row: IntelligenceIndexResult) -> dict[str, object]:
    return {
        "model_name": model.name,
        "name": PRIMARY_BENCHMARK,
        "version": row.version,
        "category": "general intelligence",
        "metric": PRIMARY_BENCHMARK_METRIC,
        "score": str(row.score),
        "evaluator": PRIMARY_EVALUATOR,
        "source_url": row.source_url,
        "source_title": row.source_title,
        "reported_date": None,
        "higher_is_better": True,
        "score_min": None,
        "score_max": None,
    }


def process_benchmark_refresh(session: Session, _config: Settings) -> int:
    job = session.scalar(
        select(BenchmarkRefresh)
        .where(BenchmarkRefresh.status.in_(["queued", "running", "blocked"]))
        .order_by(BenchmarkRefresh.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job is None:
        return 0

    items = list(
        session.scalars(
            select(BenchmarkRefreshItem)
            .where(
                BenchmarkRefreshItem.refresh_id == job.id,
                BenchmarkRefreshItem.status.in_(["queued", "running"]),
            )
            .order_by(BenchmarkRefreshItem.id)
            .with_for_update(skip_locked=True)
        )
    )
    if not items:
        job.status = "completed_with_errors" if job.failed_models else "completed"
        job.completed_at = utcnow()
        session.commit()
        return 0

    job.status = "running"
    job.error = None
    for item in items:
        item.status = "running"
        item.started_at = item.started_at or utcnow()
    session.flush()

    try:
        current = fetch_current_intelligence_index()
    except (httpx.HTTPError, ValueError):
        for item in items:
            item.status = "queued"
            item.started_at = None
        job.status = "paused"
        job.error = (
            "Artificial Analysis is unavailable or changed its public data format. "
            "No benchmark data was changed; press Resume benchmarks to try again."
        )
        session.commit()
        return 0

    models = {
        model.id: model
        for model in session.scalars(select(Model).where(Model.id.in_([i.model_id for i in items])))
    }
    matches_by_slug: dict[str, list[str]] = defaultdict(list)
    resolved: dict[str, IntelligenceIndexResult] = {}
    for item in items:
        model = models.get(item.model_id)
        if model is None:
            continue
        match = match_current_result(model.name, current)
        if match is not None:
            matches_by_slug[match.slug].append(item.id)
            resolved[item.id] = match

    for item in items:
        model, match = models.get(item.model_id), resolved.get(item.id)
        if model is None:
            item.status = "failed"
            item.error = "Catalog model no longer exists."
            job.failed_models += 1
        elif match is None or match.score is None or len(matches_by_slug[match.slug]) != 1:
            item.status = "no_evidence"
            item.error = "No unique current Artificial Analysis Intelligence Index result."
        else:
            imported = persist_research_benchmarks(
                session,
                [benchmark_candidate(model, match)],
                refresh_item_id=item.id,
                target_model_id=model.id,
            )["imported"]
            item.status = "success" if imported else "no_evidence"
            item.imported_results = imported
            item.error = None if imported else "The current result could not be stored."
            job.imported_results += imported
        item.completed_at = utcnow()
        job.processed_models += 1

    job.status = "completed_with_errors" if job.failed_models else "completed"
    job.completed_at = utcnow()
    session.commit()
    return 1
