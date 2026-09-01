"""Manual, metered, cited research. Never writes canonical market facts."""

from datetime import UTC, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from filelock import FileLock, Timeout
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fener.api_schemas import StrictInput
from fener.config import Settings, settings
from fener.db import session_dependency, utcnow
from fener.private_models import ResearchRun
from fener.research_sources import DOMAINS
from fener.security import require_admin
from fener.zai_research import PROMPT_VERSION as ZAI_PROMPT_VERSION
from fener.zai_research import fetch_zai_research

router = APIRouter(
    prefix="/api/v1/research", tags=["Manual research"], dependencies=[Depends(require_admin)]
)
DB = Annotated[Session, Depends(session_dependency)]


class ResearchInput(StrictInput):
    request_id: UUID
    provider: Literal["zai"]
    model: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=10, max_length=1500)
    acknowledge_cost: Literal[True]


def provider_configuration(config: Settings) -> dict[str, Any]:
    return {
        "provider": "zai",
        "provider_name": "Z.ai",
        "key_env": "ZAI_API_KEY",
        "configured": bool(config.zai_api_key.get_secret_value()),
        "model": config.fener_zai_research_model,
        "request_limits": "1 web search and 1 summary, up to 8,000 output tokens",
        "source_policy": "Z.ai may search broadly. Only approved-domain excerpts are passed to the model; original pages still need review.",
    }


def run_view(row: ResearchRun) -> dict[str, Any]:
    # An interrupted server can leave an attempt without a final provider response.
    started = (
        row.created_at.replace(tzinfo=UTC) if row.created_at.tzinfo is None else row.created_at
    )
    stale = row.status == "running" and started < utcnow() - timedelta(minutes=5)
    return {
        "id": row.id,
        "query": row.query,
        "model": row.model,
        "provider": row.request.get("provider", "openai"),  # Preserve old run labels.
        "status": "uncertain" if stale else row.status,
        "report": row.report,
        "error": (
            "The server did not record a completed response. Usage may have been charged. No automatic retry was made."
            if stale
            else row.error
        ),
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }


@router.get("")
def research_home(session: DB) -> dict[str, Any]:
    config = settings()
    return {
        **provider_configuration(config),
        "daily_limit": config.fener_research_daily_limit,
        "domains": DOMAINS,
        "runs": [
            run_view(row)
            for row in session.scalars(
                select(ResearchRun).order_by(ResearchRun.created_at.desc()).limit(30)
            )
        ],
    }


@router.post("", status_code=201)
def research_run(request: ResearchInput, session: DB) -> dict[str, Any]:
    existing = session.get(ResearchRun, str(request.request_id))
    if existing:
        if (
            existing.query != request.query
            or existing.model != request.model
            or existing.request.get("provider", "openai") != request.provider
        ):
            raise HTTPException(
                409, "Request ID already belongs to another question or provider/model"
            )
        return run_view(existing)
    config = settings()
    info = provider_configuration(config)
    if request.provider != info["provider"] or request.model != info["model"]:
        raise HTTPException(
            409,
            "Research provider or model changed. Refresh the page and approve the current configuration.",
        )
    key = config.zai_api_key.get_secret_value()
    if not key:
        raise HTTPException(
            503,
            f"Add {info['key_env']} to the local server .env and restart the API before running research.",
        )
    lock_path = config.fener_snapshot_dir.parent / "research.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(lock_path), timeout=0):
            used = (
                session.scalar(
                    select(func.count())
                    .select_from(ResearchRun)
                    .where(ResearchRun.created_at >= utcnow() - timedelta(hours=24))
                )
                or 0
            )
            if used >= config.fener_research_daily_limit:
                raise HTTPException(
                    429,
                    "Research request limit reached for the last 24 hours. Failed and uncertain attempts also count.",
                )
            payload = {
                "model": info["model"],
                "query": request.query,
                "search_engine": "search-prime",
                "max_search_requests": 1,
                "max_summary_requests": 1,
                "max_output_tokens": 8000,
            }
            row = ResearchRun(
                id=str(request.request_id),
                query=request.query,
                model=info["model"],
                status="running",
                request={
                    **payload,
                    "provider": request.provider,
                    "prompt_version": ZAI_PROMPT_VERSION,
                    "acknowledge_cost": True,
                },
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(
                    409, "Request already registered. Refresh research history before retrying."
                ) from None
            try:
                row.report = fetch_zai_research(payload, key)
                row.status = "needs_review"
            except httpx.HTTPError:
                row.status = "uncertain"
                row.error = "The provider connection failed or timed out. Usage may have been charged. No automatic retry was made; review this attempt before starting another."
            except (ValueError, KeyError, TypeError, AttributeError, IndexError):
                row.status = "failed"
                row.error = "Research did not return a complete, usable cited report. Check provider credentials/model access and limits. Usage may have been charged. No automatic retry was made."
            row.completed_at = utcnow()
            session.commit()
            return run_view(row)
    except Timeout:
        raise HTTPException(
            409, "Another research request is running. Wait and refresh history."
        ) from None
