"""Private, explicitly approved full-catalog benchmark refresh queue."""

from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fener.api_schemas import StrictInput
from fener.db import session_dependency
from fener.models import Model
from fener.private_models import BenchmarkRefresh, BenchmarkRefreshItem
from fener.security import require_admin

router = APIRouter(
    prefix="/api/v1/benchmark-refresh",
    tags=["Benchmark research"],
    dependencies=[Depends(require_admin)],
)
DB = Annotated[Session, Depends(session_dependency)]
RECOVERABLE_FAILURE_PREFIXES = (
    "Research validation failed: Search returned no usable excerpts",
    "Research validation failed: Incomplete benchmark candidate",
    "Research validation failed: Invalid benchmark number",
    "Research validation failed: Research provider returned HTTP 429.",
)


class RefreshInput(StrictInput):
    request_id: UUID
    acknowledge_cost: Literal[True]


def resume_refresh(session: Session, row: BenchmarkRefresh) -> None:
    recovered = 0
    for item in session.scalars(
        select(BenchmarkRefreshItem).where(
            BenchmarkRefreshItem.refresh_id == row.id,
            BenchmarkRefreshItem.status.in_(["failed", "no_evidence"]),
            BenchmarkRefreshItem.imported_results == 0,
        )
    ):
        if item.status == "no_evidence" or any(
            (item.error or "").startswith(prefix) for prefix in RECOVERABLE_FAILURE_PREFIXES
        ):
            item.status = "queued"
            item.error = None
            item.started_at = None
            item.completed_at = None
            recovered += 1
    row.processed_models = max(0, row.processed_models - recovered)
    row.failed_models = max(0, row.failed_models - recovered)
    row.status = "queued"
    row.error = None
    session.commit()


def refresh_view(session: Session, row: BenchmarkRefresh | None) -> dict[str, Any]:
    current = None
    status_counts: dict[str, int] = {}
    failure_reasons: list[dict[str, Any]] = []
    models_without_results = 0
    if row:
        current = session.execute(
            select(Model.name)
            .join(BenchmarkRefreshItem, BenchmarkRefreshItem.model_id == Model.id)
            .where(
                BenchmarkRefreshItem.refresh_id == row.id,
                BenchmarkRefreshItem.status == "running",
            )
            .limit(1)
        ).scalar_one_or_none()
        status_counts = {
            status: count
            for status, count in session.execute(
                select(BenchmarkRefreshItem.status, func.count())
                .where(BenchmarkRefreshItem.refresh_id == row.id)
                .group_by(BenchmarkRefreshItem.status)
            )
        }
        models_without_results = (
            session.scalar(
                select(func.count())
                .select_from(BenchmarkRefreshItem)
                .where(
                    BenchmarkRefreshItem.refresh_id == row.id,
                    BenchmarkRefreshItem.status.in_(["success", "no_evidence"]),
                    BenchmarkRefreshItem.imported_results == 0,
                )
            )
            or 0
        )
        failure_reasons = [
            {"message": message, "count": count}
            for message, count in session.execute(
                select(BenchmarkRefreshItem.error, func.count())
                .where(
                    BenchmarkRefreshItem.refresh_id == row.id,
                    BenchmarkRefreshItem.error.is_not(None),
                )
                .group_by(BenchmarkRefreshItem.error)
                .order_by(func.count().desc(), BenchmarkRefreshItem.error)
            )
            if message
        ]
    return {
        "configured": True,
        "model": "Artificial Analysis public dataset",
        "refresh": (
            {
                "id": row.id,
                "status": row.status,
                "total_models": row.total_models,
                "processed_models": row.processed_models,
                "imported_results": row.imported_results,
                "failed_models": row.failed_models,
                "current_model": current,
                "error": row.error,
                "item_status_counts": status_counts,
                "models_without_results": models_without_results,
                "failure_reasons": failure_reasons,
                "created_at": row.created_at,
                "completed_at": row.completed_at,
            }
            if row
            else None
        ),
    }


@router.get("")
def get_refresh(session: DB) -> dict[str, Any]:
    row = session.scalar(select(BenchmarkRefresh).order_by(BenchmarkRefresh.created_at.desc()))
    return refresh_view(session, row)


@router.post("", status_code=202)
def start_refresh(request: RefreshInput, session: DB) -> dict[str, Any]:
    existing = session.get(BenchmarkRefresh, str(request.request_id))
    if existing:
        if existing.status == "paused":
            resume_refresh(session, existing)
        return refresh_view(session, existing)
    active = session.scalar(
        select(BenchmarkRefresh).where(
            BenchmarkRefresh.status.in_(["queued", "running", "blocked", "paused"])
        )
    )
    if active:
        if active.status == "paused":
            resume_refresh(session, active)
        return refresh_view(session, active)
    model_ids = list(
        session.scalars(
            select(Model.id)
            .where(Model.identity_status == "resolved")
            .order_by(Model.name, Model.id)
        )
    )
    if not model_ids:
        raise HTTPException(409, "No resolved catalog models are available for benchmark research")
    row = BenchmarkRefresh(
        id=str(request.request_id),
        status="queued",
        model="Artificial Analysis public dataset",
        total_models=len(model_ids),
    )
    session.add(row)
    session.add_all(
        [
            BenchmarkRefreshItem(
                id=str(uuid4()), refresh_id=row.id, model_id=model_id, status="queued"
            )
            for model_id in model_ids
        ]
    )
    session.commit()
    return refresh_view(session, row)
