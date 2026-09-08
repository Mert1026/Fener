from datetime import datetime
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from fener.evidence import EvidenceWriter, digest, json_value
from fener.models import (
    BenchmarkDefinition,
    BenchmarkResult,
    Deployment,
    DeploymentAlias,
    Fact,
    MarketEvent,
    Model,
    ModelAlias,
    Organization,
    Price,
    Provider,
    SourceRecord,
)
from fener.sources.contracts import NormalizedRecord
from fener.value_comparison import equal_values

log = structlog.get_logger()


class CatalogWriter:
    def __init__(self, session: Session, source_id: str, observed_at: datetime):
        self.session, self.source_id, self.observed_at = session, source_id, observed_at
        self.evidence = EvidenceWriter(session, source_id, observed_at)
        self.models = {r.identity_key: r for r in session.scalars(select(Model))}
        self.models_by_id = {r.id: r for r in self.models.values()}
        self.providers = {r.id: r for r in session.scalars(select(Provider))}
        self.organizations = {r.id: r for r in session.scalars(select(Organization))}
        self.aliases = {
            (r.source_id, r.external_id): r for r in session.scalars(select(ModelAlias))
        }
        self.deployments = {r.id: r for r in session.scalars(select(Deployment))}
        self.deployment_aliases = {r.id for r in session.scalars(select(DeploymentAlias))}
        self.records = {
            r.id: r
            for r in session.scalars(
                select(SourceRecord).where(SourceRecord.source_id == source_id)
            )
        }
        self.benchmarks = {r.id for r in session.scalars(select(BenchmarkDefinition))}
        self.results = {r.id for r in session.scalars(select(BenchmarkResult))}
        # Values already observed during this sync. Several upstream entries can
        # resolve to the same deployment (e.g. LiteLLM lists `gemini/exp-1206`
        # and `gemini/gemini-exp-1206`); without this guard they overwrite each
        # other every sync and emit contradictory change events forever.
        self.sync_values: dict[tuple[str, str, str], object] = {}

    def observe_once(
        self,
        entity_type: str,
        entity_id: str,
        field: str,
        value: object,
        record: SourceRecord,
        authority: int,
        verification: str,
    ) -> tuple[Fact | None, bool]:
        key = (entity_type, entity_id, field)
        if key in self.sync_values:
            if not equal_values(field, self.sync_values[key], value):
                log.warning(
                    "conflicting_source_entries_skipped",
                    source_id=self.source_id,
                    external_id=record.external_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    field=field,
                )
            return None, False
        self.sync_values[key] = value
        return self.evidence.observe(
            entity_type, entity_id, field, value, record, authority, verification
        )

    def provider(self, provider_id: str, name: str) -> None:
        if provider_id not in self.providers:
            provider = Provider(
                id=provider_id,
                name=name,
                kind="marketplace" if provider_id == "openrouter" else "unknown",
            )
            self.session.add(provider)
            self.providers[provider_id] = provider
            self.session.flush()

    def persist(self, row: NormalizedRecord, snapshot_id: str, url: str) -> bool:
        record_id = digest(self.source_id, row.external_id, row.raw)
        record = self.records.get(record_id)
        if record is None:
            record = SourceRecord(
                id=record_id,
                source_id=self.source_id,
                snapshot_id=snapshot_id,
                external_id=row.external_id,
                source_url=url,
                raw=json_value(row.raw),
                observed_at=self.observed_at,
                last_seen_at=self.observed_at,
            )
            self.records[record_id] = record
            self.session.add(record)
            self.session.flush()
        else:
            record.last_seen_at = self.observed_at
        alias = self.aliases.get((self.source_id, row.external_id))
        model = self.models_by_id.get(alias.model_id) if alias else None
        canonical_key = f"canonical:{row.canonical_id}"
        if model is None:
            model = self.models.get(canonical_key) if row.canonical_id else None
        # Exact access provider + API identifier + serving variant is strong
        # deployment evidence. Reuse its model before making a source candidate.
        if model is None and row.provider_id and row.api_id:
            variant = "routing" if row.listing_kind == "routing_quote" else row.variant
            existing = self.deployments.get(digest(row.provider_id, row.api_id, variant))
            if existing:
                model = self.models_by_id[existing.model_id]
        # A source may gain enough exact identity information after a candidate
        # was first discovered. Promote that same row in place so its aliases,
        # deployments, evidence, and history retain stable IDs.
        promoted_identity = False
        if model is not None and row.canonical and model.identity_status != "resolved":
            canonical_model = self.models.get(canonical_key)
            if canonical_model is None or canonical_model.id == model.id:
                self.models.pop(model.identity_key, None)
                model.identity_key = canonical_key
                model.identity_status = "resolved"
                if row.publisher_id:
                    if row.publisher_id not in self.organizations:
                        organization = Organization(id=row.publisher_id, name=row.publisher_id)
                        self.session.add(organization)
                        self.organizations[organization.id] = organization
                        self.session.flush()
                model.publisher_id = row.publisher_id
                self.models[canonical_key] = model
                promoted_identity = True
        new_model = model is None
        if model is None:
            key = (
                canonical_key
                if row.canonical
                else f"candidate:{self.source_id}:{row.canonical_id or row.external_id}"
            )
            model = self.models.get(key)
            if model is None:
                if row.publisher_id and row.publisher_id not in self.organizations:
                    org = Organization(id=row.publisher_id, name=row.publisher_id)
                    self.session.add(org)
                    self.organizations[org.id] = org
                    self.session.flush()
                model = Model(
                    id=digest(key),
                    identity_key=key,
                    name=row.name,
                    publisher_id=row.publisher_id,
                    identity_status="resolved" if row.canonical else "unresolved",
                )
                self.models[key] = model
                self.models_by_id[model.id] = model
                self.session.add(model)
                self.session.flush()
                self.session.add(
                    MarketEvent(
                        id=digest("new_model", model.id),
                        event_type="new_model",
                        entity_type="model",
                        entity_id=model.id,
                        title=f"Discovered {row.name}",
                        source_record_id=record.id,
                        new_value=row.name,
                        importance="medium",
                    )
                )
        if not alias:
            alias = ModelAlias(
                id=digest(self.source_id, row.external_id),
                source_id=self.source_id,
                external_id=row.external_id,
                model_id=model.id,
                evidence_id=record.id,
            )
            self.session.add(alias)
            self.aliases[(self.source_id, row.external_id)] = alias
        changed = new_model or promoted_identity
        for field, value in {"name": row.name, **row.model_facts}.items():
            # Deployment labels are evidence but cannot overwrite canonical model names.
            if field == "name" and not row.canonical and not new_model:
                continue
            _, update = self.observe_once(
                "model", model.id, field, value, record, 60 if row.canonical else 20, "aggregated"
            )
            changed |= update
        if row.provider_id and row.api_id:
            self.provider(row.provider_id, row.provider_name or row.provider_id)
            upstream = row.upstream_id.lower().replace(" ", "-") if row.upstream_id else None
            if not upstream and row.provider_id == model.publisher_id:
                upstream = row.provider_id
            if upstream:
                self.provider(upstream, row.upstream_id or upstream)
            variant = "routing" if row.listing_kind == "routing_quote" else row.variant
            deployment_id = digest(row.provider_id, row.api_id, variant)
            if deployment_id not in self.deployments:
                deployment = Deployment(
                    id=deployment_id,
                    model_id=model.id,
                    access_provider_id=row.provider_id,
                    upstream_provider_id=upstream,
                    api_model_id=row.api_id,
                    variant=variant,
                    listing_kind=row.listing_kind,
                )
                self.session.add(deployment)
                self.deployments[deployment_id] = deployment
                self.session.flush()
                self.session.add(
                    MarketEvent(
                        id=digest("new_deployment", deployment_id),
                        event_type="new_deployment",
                        entity_type="deployment",
                        entity_id=deployment_id,
                        title=f"{row.name} via {row.provider_name}",
                        source_record_id=record.id,
                        importance="low",
                    )
                )
                changed = True
            alias_id = digest("deployment_alias", self.source_id, row.external_id)
            if alias_id not in self.deployment_aliases:
                self.session.add(
                    DeploymentAlias(
                        id=alias_id,
                        source_id=self.source_id,
                        external_id=row.external_id,
                        deployment_id=deployment_id,
                        evidence_id=record.id,
                    )
                )
                self.deployment_aliases.add(alias_id)
            authority = (
                100
                if self.source_id == "openrouter"
                else 50
                if self.source_id == "models_dev"
                else 40
            )
            verification = "official" if self.source_id == "openrouter" else "aggregated"
            deployment_facts = dict(row.deployment_facts)
            if row.provider_url:
                self.observe_once(
                    "provider",
                    row.provider_id,
                    "documentation_url",
                    row.provider_url,
                    record,
                    authority,
                    verification,
                )
            for field, value in deployment_facts.items():
                _, update = self.observe_once(
                    "deployment", deployment_id, field, value, record, authority, verification
                )
                changed |= update
            for price in row.prices:
                amount = price.normalized
                value = {
                    "amount": str(amount),
                    "currency": "USD",
                    "quantity": 1_000_000 if price.unit == "tokens" else 1,
                    "unit": price.unit,
                }
                fact, update = self.observe_once(
                    "deployment",
                    deployment_id,
                    f"price.{price.metric}",
                    value,
                    record,
                    authority,
                    verification,
                )
                if update:
                    assert fact is not None
                    self.session.add(
                        Price(
                            id=fact.id,
                            deployment_id=deployment_id,
                            metric=price.metric,
                            amount=amount,
                            quantity=value["quantity"],
                            unit=price.unit,
                            source_record_id=record.id,
                            native_amount=str(price.amount),
                            native_quantity=price.quantity,
                            observed_at=self.observed_at,
                        )
                    )
                    changed = True
        self.persist_benchmarks(row, model, record)
        return changed

    def persist_benchmarks(self, row: NormalizedRecord, model: Model, record: SourceRecord) -> None:
        for benchmark in row.benchmarks:
            if not isinstance(benchmark, dict) or not isinstance(benchmark.get("name"), str):
                raise ValueError("Invalid benchmark record")
            if benchmark.get("score") is None or not benchmark.get("source"):
                continue
            # An unspecified methodology is isolated by model/evidence; it is not cross-model comparable.
            version = str(benchmark.get("version") or f"unspecified:{model.id[:12]}")
            benchmark_id = digest(benchmark["name"], version)
            if benchmark_id not in self.benchmarks:
                self.session.add(
                    BenchmarkDefinition(
                        id=benchmark_id,
                        name=benchmark["name"],
                        version=version,
                        category="unclassified",
                        source_record_id=record.id,
                    )
                )
                self.session.flush()
                self.benchmarks.add(benchmark_id)
            result_id = digest(benchmark_id, model.id, benchmark)
            if result_id not in self.results:
                score = Decimal(str(benchmark["score"]))
                if not score.is_finite():
                    raise ValueError("Nonfinite benchmark score")
                self.session.add(
                    BenchmarkResult(
                        id=result_id,
                        model_id=model.id,
                        benchmark_id=benchmark_id,
                        score=score,
                        verification="aggregated",
                        evaluator="Unspecified by catalog",
                        source_record_id=record.id,
                    )
                )
                self.results.add(result_id)
