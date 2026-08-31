import time
from collections import defaultdict, deque
from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Any, Literal
from uuid import uuid4

import structlog
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fener.analytics import comparable_scores
from fener.api_schemas import DeploymentView, ModelDetail, ModelPage, ProviderView
from fener.catalog import (
    benchmark_results,
    deployment_views,
    facts_for,
    list_models,
    provider_views,
    summarize,
)
from fener.db import session_dependency
from fener.models import (
    Conflict,
    Deployment,
    Fact,
    IngestionRun,
    MarketEvent,
    Model,
    Price,
    Provider,
    RecommendationRun,
    Source,
    SourceClaim,
    SourceRecord,
)
from fener.private_api import router as private_router
from fener.recommendations import (
    ALGORITHM_VERSION,
    RecommendationInput,
    Workload,
    estimate_cost,
    pareto_ids,
    recommend,
)
from fener.security import require_admin

app = FastAPI(
    title="Fener Model Intelligence",
    version="0.1.0",
    description="Source-backed market data and deterministic workload recommendations.",
)
app.include_router(private_router)
DB = Annotated[Session, Depends(session_dependency)]
Admin = Annotated[None, Depends(require_admin)]
log = structlog.get_logger()
windows: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def request_context(request: Request, call_next: Any) -> Any:
    request.state.request_id = str(uuid4())
    if request.method == "POST":
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        if key not in windows and len(windows) >= 4096:
            windows.clear()
        window = windows[key]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= 30:
            return JSONResponse(
                {"code": "rate_limited", "message": "Retry after one minute"},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        window.append(now)
        size = request.headers.get("content-length", "0")
        if not size.isdigit() or int(size) > 131072:
            return JSONResponse(
                {"code": "body_too_large", "message": "Maximum body size is 128 KiB"},
                status_code=413,
            )
        # Enforce the actual streamed size too; chunked bodies have no length header.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 131072:
                return JSONResponse(
                    {"code": "body_too_large", "message": "Maximum body size is 128 KiB"},
                    status_code=413,
                )
        request._body = bytes(body)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException) -> JSONResponse:
    return JSONResponse(
        {
            "code": f"http_{error.status_code}",
            "message": str(error.detail),
            "request_id": request.state.request_id,
        },
        status_code=error.status_code,
        headers=error.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    message = "; ".join(
        ".".join(map(str, item["loc"])) + ": " + item["msg"] for item in error.errors()
    )
    return JSONResponse(
        {"code": "invalid_input", "message": message, "request_id": request.state.request_id},
        status_code=422,
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
    log.error(
        "database_error", request_id=request.state.request_id, error_type=type(error).__name__
    )
    return JSONResponse(
        {
            "code": "database_unavailable",
            "message": "Database unavailable. Check infrastructure and run migrations.",
            "request_id": request.state.request_id,
        },
        status_code=503,
    )


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def ready(session: DB) -> dict[str, str]:
    versions = set(session.scalars(text("SELECT version_num FROM alembic_version")))
    if versions != {migration_head()}:
        raise HTTPException(503, "Database migrations are not current; run alembic upgrade head")
    return {"status": "ready"}


@lru_cache
def migration_head() -> str | None:
    return ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()


@app.get("/api/v1/models", response_model=ModelPage)
def models(
    session: DB,
    q: str = Query(default="", max_length=200),
    publisher: str | None = None,
    provider: str | None = None,
    capability: Literal["tool_calling", "reasoning", "image_input", "structured_output"]
    | None = None,
    min_context: int = Query(default=0, ge=0),
    open_weights: bool | None = None,
    include_unresolved: bool = False,
    sort: Literal["name", "context", "released"] = "name",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> ModelPage:
    return list_models(
        session,
        q,
        publisher,
        provider,
        capability,
        min_context,
        open_weights,
        include_unresolved,
        sort,
        offset,
        limit,
    )


@app.get("/api/v1/models/{model_id}", response_model=ModelDetail)
def model_detail(model_id: str, session: DB) -> ModelDetail:
    model = session.get(Model, model_id)
    if model is None:
        raise HTTPException(404, "Model not found")
    return ModelDetail(
        model=summarize(session, [model])[0],
        deployments=deployment_views(session, [model_id], limit=500),
        benchmarks=benchmark_results(session, model_id),
    )


@app.get("/api/v1/models/{model_id}/deployments", response_model=list[DeploymentView])
def model_deployments(
    model_id: str, session: DB, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)
) -> list[DeploymentView]:
    return deployment_views(session, [model_id], limit=limit, offset=offset)


@app.get("/api/v1/deployments", response_model=list[DeploymentView])
def deployments(
    session: DB,
    provider: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[DeploymentView]:
    return deployment_views(session, provider=provider, offset=offset, limit=limit)


@app.get("/api/v1/providers", response_model=list[ProviderView])
def providers(session: DB) -> list[ProviderView]:
    return provider_views(session)


@app.get("/api/v1/providers/{provider_id}")
def provider_detail(
    provider_id: str,
    session: DB,
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
) -> dict[str, Any]:
    provider = next((p for p in provider_views(session) if p.id == provider_id), None)
    if not provider:
        raise HTTPException(404, "Provider not found")
    return {
        "provider": provider,
        "deployments": deployment_views(session, provider=provider_id, offset=offset, limit=limit),
    }


@app.get("/api/v1/models/{model_id}/pricing")
def pricing(
    model_id: str, session: DB, limit: int = Query(200, ge=1, le=1000)
) -> list[dict[str, Any]]:
    query = (
        select(Price, Deployment, SourceRecord, Fact)
        .join(Deployment, Price.deployment_id == Deployment.id)
        .join(SourceRecord, Price.source_record_id == SourceRecord.id)
        .join(Fact, Price.id == Fact.id)
        .where(Deployment.model_id == model_id)
        .order_by(Price.observed_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": price.id,
            "deployment_id": price.deployment_id,
            "provider": deployment.access_provider_id,
            "metric": price.metric,
            "amount": fact.value["amount"],
            "native_amount": price.native_amount,
            "quantity": price.quantity,
            "unit": price.unit,
            "currency": price.currency,
            "observed_at": price.observed_at,
            "source": record.source_id,
            "source_url": record.source_url,
        }
        for price, deployment, record, fact in session.execute(query)
    ]


@app.get("/api/v1/benchmarks")
def benchmarks(
    session: DB,
    model_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    return benchmark_results(session, model_id, limit, offset)


@app.get("/api/v1/market-events")
def market_events(
    session: DB,
    event_type: str | None = None,
    entity_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    query = (
        select(MarketEvent, SourceRecord, Model.id, Model.name, Deployment.access_provider_id)
        .join(SourceRecord, MarketEvent.source_record_id == SourceRecord.id)
        .outerjoin(
            Deployment,
            (MarketEvent.entity_type == "deployment") & (MarketEvent.entity_id == Deployment.id),
        )
        .outerjoin(Model, Model.id == func.coalesce(Deployment.model_id, MarketEvent.entity_id))
    )
    if event_type:
        query = query.where(MarketEvent.event_type == event_type)
    if entity_id:
        query = query.where(MarketEvent.entity_id == entity_id)
    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "title": f"{name}{' via ' + provider if provider else ''}: {event.title}"
            if name and event.event_type.endswith("_change")
            else event.title,
            "model_id": model_id,
            "old_value": event.old_value,
            "new_value": event.new_value,
            "importance": event.importance,
            "detected_at": event.detected_at,
            "source": record.source_id,
            "source_url": record.source_url,
        }
        for event, record, model_id, name, provider in session.execute(
            query.order_by(MarketEvent.detected_at.desc(), MarketEvent.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@app.get("/api/v1/observations/{observation_id}")
def observation(observation_id: str, session: DB) -> dict[str, Any]:
    fact = session.get(Fact, observation_id)
    if not fact:
        raise HTTPException(404, "Observation not found")
    record = session.get(SourceRecord, fact.source_record_id)
    assert record is not None
    claim = session.scalar(select(SourceClaim).where(SourceClaim.observation_id == fact.id))
    return {
        "id": fact.id,
        "field": fact.field,
        "normalized_value": fact.value,
        "raw_record": record.raw,
        "source": record.source_id,
        "source_url": record.source_url,
        "snapshot_id": record.snapshot_id,
        "observed_at": fact.observed_at,
        "last_seen_at": claim.last_seen_at if claim and claim.last_seen_at else record.last_seen_at,
        "confirming_record_id": claim.confirming_record_id if claim else None,
        "verification": fact.verification,
    }


@app.get("/api/v1/sources")
def sources(session: DB) -> list[dict[str, Any]]:
    return [
        {
            "id": source.id,
            "name": source.name,
            "url": source.url,
            "terms_url": source.terms_url,
            "attribution": source.attribution,
            "status": source.status,
            "last_success_at": source.last_success_at,
            "interval_seconds": source.interval_seconds,
        }
        for source in session.scalars(select(Source).order_by(Source.name))
    ]


@app.get("/api/v1/overview")
def overview(session: DB) -> dict[str, Any]:
    def count(table: Any) -> int:
        return session.scalar(select(func.count()).select_from(table)) or 0

    return {
        "models": session.scalar(
            select(func.count()).select_from(Model).where(Model.identity_status == "resolved")
        )
        or 0,
        "unresolved_models": session.scalar(
            select(func.count()).select_from(Model).where(Model.identity_status != "resolved")
        )
        or 0,
        "deployments": count(Deployment),
        "providers": count(Provider),
        "observations": count(Fact),
        "sources": sources(session),
        "recent_events": market_events(session, limit=6, offset=0),
        "recent_models": list_models(session, sort="released", limit=6).items,
    }


def recommendation_result(session: Session, request: RecommendationInput) -> dict[str, Any]:
    # Bound the working set; disclose truncation instead of implying full-market coverage.
    candidates = deployment_views(session, limit=10000)
    model_ids = list({d.model_id for d in candidates})
    model_facts = facts_for(session, "model", model_ids)
    benchmark_scores, benchmark_evidence = comparable_scores(session)
    result = recommend(
        candidates,
        request,
        {id: {k: v.value for k, v in facts.items()} for id, facts in model_facts.items()},
        benchmark_scores,
    )
    result["benchmark_evidence"] = [r for r in benchmark_evidence if r["metric"] in request.weights]
    result["candidate_limit"] = 10000
    result["candidate_limit_reached"] = len(candidates) == 10000
    return result


@app.post("/api/v1/recommendations/preview")
def recommendation_preview(request: RecommendationInput, session: DB) -> dict[str, Any]:
    return recommendation_result(session, request)


@app.post("/api/v1/recommendations")
def recommendations(request: RecommendationInput, session: DB, _: Admin) -> dict[str, Any]:
    result = recommendation_result(session, request)
    run_id = str(uuid4())
    session.add(
        RecommendationRun(
            id=run_id,
            algorithm_version=ALGORITHM_VERSION,
            request=request.model_dump(mode="json"),
            response=result,
        )
    )
    session.commit()
    return {"recommendation_id": run_id, **result}


@app.post("/api/v1/deployments/{deployment_id}/cost")
def deployment_cost(deployment_id: str, request: Workload, session: DB) -> dict[str, Any]:
    deployment = session.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(404, "Deployment not found")
    view = next(
        d
        for d in deployment_views(session, [deployment.model_id], limit=1000)
        if d.id == deployment_id
    )
    return estimate_cost(view, request)


@app.get("/api/v1/analytics/benchmarks")
def normalized_benchmarks(session: DB) -> list[dict[str, Any]]:
    return comparable_scores(session)[1]


@app.post("/api/v1/analytics/frontier")
def frontier(request: RecommendationInput, session: DB) -> dict[str, Any]:
    scores, evidence = comparable_scores(session)
    benchmark_keys = {
        key.removeprefix("benchmark:"): weight
        for key, weight in request.weights.items()
        if key.startswith("benchmark:") and weight > 0
    }
    if not benchmark_keys:
        return {
            "points": [],
            "reason": "Choose explicit versioned benchmark weights; price alone cannot define a quality frontier.",
        }
    # All frontier candidates must cover the same quality dimensions. Partial
    # coverage is retained in recommendations but excluded from dominance claims.
    deployments = deployment_views(session, limit=10000)
    facts = facts_for(session, "model", list({d.model_id for d in deployments}))
    intrinsic = {id: {k: v.value for k, v in f.items()} for id, f in facts.items()}
    points = []
    for deployment in deployments:
        values = scores.get(deployment.model_id, {})
        if not all(key in values for key in benchmark_keys):
            continue
        accepted = recommend(
            [deployment],
            request,
            intrinsic,
            scores,
        )
        if accepted["recommended"] is None:
            continue
        cost = accepted["recommended"]["estimated_cost"]
        quality = sum(
            (values[key] * weight for key, weight in benchmark_keys.items()), Decimal(0)
        ) / sum(benchmark_keys.values())
        points.append(
            {
                "deployment_id": deployment.id,
                "model_id": deployment.model_id,
                "model_name": deployment.model_name,
                "provider": deployment.access_provider,
                "cost": cost,
                "quality": str(quality),
            }
        )
    ids = pareto_ids(
        [(p["deployment_id"], Decimal(p["cost"]), Decimal(p["quality"])) for p in points]
    )
    return {
        "points": [{**p, "pareto": p["deployment_id"] in ids} for p in points],
        "evidence": [r for r in evidence if r["metric"] in request.weights],
        "candidate_limit": 10000,
        "candidate_limit_reached": len(deployments) == 10000,
        "reason": None
        if points
        else "No candidates have complete comparable quality evidence and satisfy these constraints.",
    }


@app.get("/api/v1/data-health")
def data_health(session: DB, _: Admin) -> dict[str, Any]:
    runs = list(
        session.scalars(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(50))
    )
    conflicts = list(session.scalars(select(Conflict).order_by(Conflict.id).limit(100)))
    return {
        "sources": sources(session),
        "runs": [
            {
                "id": r.id,
                "source_id": r.source_id,
                "status": r.status,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "records_discovered": r.records_discovered,
                "records_changed": r.records_changed,
                "error": r.error,
            }
            for r in runs
        ],
        "conflicts": [
            {
                "id": c.id,
                "entity_id": c.entity_id,
                "field": c.field,
                "status": c.status,
                "observation_a": c.observation_a,
                "observation_b": c.observation_b,
                "resolution": c.resolution,
            }
            for c in conflicts
        ],
        "unresolved_models": session.scalar(
            select(func.count()).select_from(Model).where(Model.identity_status == "unresolved")
        ),
        "conflict_count": session.scalar(select(func.count()).select_from(Conflict)),
    }
