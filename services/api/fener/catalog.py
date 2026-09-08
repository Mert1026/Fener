from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from fener.api_schemas import DeploymentView, EvidenceView, ModelPage, ModelView, ProviderView
from fener.models import (
    CurrentFact,
    Deployment,
    Fact,
    Model,
    ModelAlias,
    Provider,
    ResearchBenchmark,
    SourceClaim,
    SourceRecord,
)


def facts_for(session: Session, kind: str, ids: list[str]) -> dict[str, dict[str, EvidenceView]]:
    result: dict[str, dict[str, EvidenceView]] = {id: {} for id in ids}
    if not ids:
        return result
    query = (
        select(
            Fact,
            SourceRecord.source_id,
            SourceRecord.source_url,
            func.coalesce(SourceClaim.last_seen_at, SourceRecord.last_seen_at),
        )
        .join(CurrentFact, CurrentFact.observation_id == Fact.id)
        .join(SourceRecord, Fact.source_record_id == SourceRecord.id)
        .join(SourceClaim, SourceClaim.observation_id == Fact.id)
        .where(CurrentFact.entity_type == kind, CurrentFact.entity_id.in_(ids))
    )
    for fact, source_id, source_url, last_seen_at in session.execute(query):
        seen = last_seen_at.replace(tzinfo=UTC)
        result[fact.entity_id][fact.field] = EvidenceView(
            id=fact.id,
            value=fact.value,
            source=source_id,
            source_url=source_url,
            observed_at=fact.observed_at,
            last_seen_at=seen,
            verification=fact.verification,
            stale=(datetime.now(UTC) - seen).total_seconds() > 48 * 3600,
        )
    return result


def deployment_views(
    session: Session,
    model_ids: list[str] | None = None,
    provider: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[DeploymentView]:
    query = select(Deployment, Model.name, Model.identity_status).join(Model)
    if model_ids is not None:
        query = query.where(Deployment.model_id.in_(model_ids))
    if provider:
        query = query.where(Deployment.access_provider_id == provider)
    rows = session.execute(
        query.order_by(Model.name, Deployment.access_provider_id, Deployment.id)
        .offset(offset)
        .limit(limit)
    ).all()
    facts = facts_for(session, "deployment", [row.id for row, _, _ in rows])
    provider_facts = facts_for(
        session, "provider", sorted({row.access_provider_id for row, _, _ in rows})
    )

    def provider_url(access_provider: str) -> str | None:
        fact = provider_facts.get(access_provider, {}).get("documentation_url")
        value = fact.value if fact else None
        return value if isinstance(value, str) and value.startswith("http") else None

    return [
        DeploymentView(
            id=row.id,
            model_id=row.model_id,
            model_name=name,
            identity_status=identity_status,
            access_provider=row.access_provider_id,
            provider_url=provider_url(row.access_provider_id),
            upstream_provider=row.upstream_provider_id,
            api_model_id=row.api_model_id,
            variant=row.variant,
            listing_kind=row.listing_kind,
            facts=facts[row.id],
        )
        for row, name, identity_status in rows
    ]


def summarize(session: Session, models: list[Model]) -> list[ModelView]:
    ids = [row.id for row in models]
    facts = facts_for(session, "model", ids)
    deployment_ids = list(
        session.execute(
            select(Deployment.id, Deployment.model_id).where(Deployment.model_id.in_(ids))
        )
    )
    deployment_facts = facts_for(session, "deployment", [row.id for row in deployment_ids])
    grouped: dict[str, list[dict[str, EvidenceView]]] = {id: [] for id in ids}
    for deployment_id, model_id in deployment_ids:
        grouped[model_id].append(deployment_facts[deployment_id])

    def cheapest(items: list[dict[str, EvidenceView]], field: str) -> EvidenceView | None:
        values = [
            item[field]
            for item in items
            if field in item and item[field].value["currency"] == "USD"
        ]
        return min(values, key=lambda v: Decimal(v.value["amount"])) if values else None

    prices = {
        id: (cheapest(items, "price.input_tokens"), cheapest(items, "price.output_tokens"))
        for id, items in grouped.items()
    }

    def amount(fact: EvidenceView | None) -> str | None:
        return str(fact.value["amount"]) if fact else None

    return [
        ModelView(
            id=row.id,
            name=row.name,
            publisher=row.publisher_id,
            family=row.family,
            context_window=row.context_window,
            open_weights=row.open_weights,
            release_date=row.release_date,
            identity_status=row.identity_status,
            deployment_count=len(grouped[row.id]),
            input_price_from=amount(prices[row.id][0]),
            output_price_from=amount(prices[row.id][1]),
            input_price_evidence=prices[row.id][0],
            output_price_evidence=prices[row.id][1],
            capabilities=sorted(k for k, v in facts[row.id].items() if v.value is True),
            facts=facts[row.id],
        )
        for row in models
    ]


def list_models(
    session: Session,
    q: str = "",
    publisher: str | None = None,
    provider: str | None = None,
    capability: str | None = None,
    min_context: int = 0,
    open_weights: bool | None = None,
    include_unresolved: bool = False,
    sort: str = "name",
    offset: int = 0,
    limit: int = 50,
) -> ModelPage:
    query = select(Model)
    # Exact searches should find fresh source discoveries immediately. Their
    # unresolved status remains visible and broad browsing stays canonical-only.
    if not include_unresolved and not q.strip():
        query = query.where(Model.identity_status == "resolved")
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        query = query.where(
            or_(
                Model.name.ilike(pattern, escape="\\"),
                Model.publisher_id.ilike(pattern, escape="\\"),
                Model.family.ilike(pattern, escape="\\"),
                exists(
                    select(ModelAlias.id).where(
                        ModelAlias.model_id == Model.id,
                        ModelAlias.external_id.ilike(pattern, escape="\\"),
                    )
                ),
            )
        )
    if publisher:
        query = query.where(Model.publisher_id == publisher)
    if open_weights is not None:
        query = query.where(Model.open_weights.is_(open_weights))
    if min_context:
        query = query.where(Model.context_window >= min_context)
    if provider or capability:
        condition = select(Deployment.id).where(Deployment.model_id == Model.id)
        if provider:
            condition = condition.where(Deployment.access_provider_id == provider)
        if capability in {"tool_calling", "reasoning", "image_input", "structured_output"}:
            condition = condition.where(getattr(Deployment, capability).is_(True))
        query = query.where(exists(condition))
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    order = (
        Model.context_window.desc().nulls_last()
        if sort == "context"
        else Model.release_date.desc().nulls_last()
        if sort == "released"
        else Model.name.asc()
    )
    models = list(session.scalars(query.order_by(order, Model.id).offset(offset).limit(limit)))
    return ModelPage(items=summarize(session, models), total=total, limit=limit, offset=offset)


def provider_views(session: Session) -> list[ProviderView]:
    rows = list(session.scalars(select(Provider).order_by(Provider.name)))
    counts = {
        provider_id: count
        for provider_id, count in session.execute(
            select(Deployment.access_provider_id, func.count()).group_by(
                Deployment.access_provider_id
            )
        ).all()
    }
    facts = facts_for(session, "provider", [row.id for row in rows])
    return [
        ProviderView(
            id=row.id,
            name=row.name,
            kind=row.kind,
            deployment_count=counts.get(row.id, 0),
            facts=facts[row.id],
        )
        for row in rows
    ]


def benchmark_results(
    session: Session,
    model_id: str | None = None,
    limit: int | None = 100,
    offset: int = 0,
    group_id: str | None = None,
) -> list[dict[str, Any]]:
    from fener.evidence import digest

    query = select(ResearchBenchmark, Model.name).join(
        Model, ResearchBenchmark.model_id == Model.id
    )
    if model_id:
        query = query.where(ResearchBenchmark.model_id == model_id)
    rows = session.execute(
        query.order_by(ResearchBenchmark.created_at.desc(), ResearchBenchmark.id)
    )
    latest = {}
    for result, model_name in rows:
        result_group = digest(
            result.name.casefold().strip(),
            result.version.casefold().strip(),
            result.evaluator.casefold().strip(),
            result.metric.casefold().strip(),
        )
        if group_id and result_group != group_id:
            continue
        key = (result.model_id, result.name, result.version, result.evaluator, result.metric)
        if key in latest:
            continue
        issues = ["Source-extracted result requires review against the cited report"]
        method_complete = not any(
            value.casefold().startswith("unspecified")
            for value in (result.version, result.evaluator, result.metric)
        )
        if (
            result.score_min is None
            or result.score_max is None
            or result.score_max <= result.score_min
        ):
            issues.append("Documented numeric scale not supplied")
        elif not result.score_min <= result.score <= result.score_max:
            issues.append("Score falls outside the documented scale")
            method_complete = False
        if result.higher_is_better is None:
            issues.append("Score direction not supplied")
            method_complete = False
        latest[key] = {
            "id": result.id,
            "model_id": result.model_id,
            "model_name": model_name,
            "benchmark_id": digest("research-benchmark", result.name, result.version),
            "name": result.name,
            "version": result.version,
            "category": result.category,
            "score": str(result.score),
            "score_min": str(result.score_min) if result.score_min is not None else None,
            "score_max": str(result.score_max) if result.score_max is not None else None,
            "higher_is_better": result.higher_is_better,
            "verification": "source_extracted_unverified",
            "evaluator": result.evaluator,
            "source": "Artificial Analysis public dataset",
            "source_url": result.source_url,
            "source_title": result.source_title,
            "observed_at": result.created_at,
            "metric": result.metric,
            "group_id": result_group,
            "report_url": result.source_url,
            "reported_date": result.reported_date,
            "quality_issues": issues,
            "comparable": method_complete,
        }
    return sorted(
        latest.values(), key=lambda r: (r["name"], r["metric"], r["model_name"], r["id"])
    )[offset : offset + limit if limit is not None else None]


def benchmark_groups(session: Session) -> list[dict[str, Any]]:
    from collections import defaultdict

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in benchmark_results(session, limit=None):
        groups[row["group_id"]].append(row)
    return [
        {
            "id": id,
            "name": rows[0]["name"],
            "version": rows[0]["version"],
            "evaluator": rows[0]["evaluator"],
            "metric": rows[0]["metric"],
            "results": len(rows),
            "models": len({r["model_id"] for r in rows}),
            "comparable_results": sum(r["comparable"] for r in rows),
        }
        for id, rows in groups.items()
    ]
