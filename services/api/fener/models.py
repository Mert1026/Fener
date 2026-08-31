"""Relational catalog and append-only evidence. Migrations own schema changes."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from fener.db import Base, utcnow


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(300), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))


class Provider(Base):
    __tablename__ = "providers"
    id: Mapped[str] = mapped_column(String(300), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(40), default="unknown")
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"))


class Model(Base):
    __tablename__ = "models"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    identity_key: Mapped[str] = mapped_column(String(800), unique=True)
    name: Mapped[str] = mapped_column(String(500), index=True)
    family: Mapped[str | None] = mapped_column(String(300), index=True)
    context_window: Mapped[int | None]
    open_weights: Mapped[bool | None]
    release_date: Mapped[str | None] = mapped_column(String(40))
    publisher_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    identity_status: Mapped[str] = mapped_column(String(30), default="unresolved")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(Text)
    terms_url: Mapped[str] = mapped_column(Text)
    attribution: Mapped[str] = mapped_column(Text)
    interval_seconds: Mapped[int] = mapped_column(default=21600)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(40), default="never_synced")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="running")
    http_status: Mapped[int | None]
    records_discovered: Mapped[int] = mapped_column(default=0)
    records_changed: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)


class Snapshot(Base):
    __tablename__ = "raw_snapshots"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    byte_length: Mapped[int]


class FetchReceipt(Base):
    __tablename__ = "fetch_receipts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("ingestion_runs.id"), index=True)
    snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("raw_snapshots.id"))
    url: Mapped[str] = mapped_column(Text)
    status: Mapped[int]
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SourceRecord(Base):
    __tablename__ = "source_records"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("raw_snapshots.id"))
    external_id: Mapped[str] = mapped_column(String(800))
    source_url: Mapped[str] = mapped_column(Text)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ModelAlias(Base):
    __tablename__ = "model_aliases"
    __table_args__ = (UniqueConstraint("source_id", "external_id"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column(String(800))
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("source_records.id"))


class Deployment(Base):
    __tablename__ = "deployments"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), index=True)
    access_provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), index=True)
    upstream_provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"))
    api_model_id: Mapped[str] = mapped_column(String(800))
    variant: Mapped[str] = mapped_column(String(500), default="default")
    listing_kind: Mapped[str] = mapped_column(String(40), default="deployment")
    context_window: Mapped[int | None]
    max_output: Mapped[int | None]
    tool_calling: Mapped[bool | None]
    structured_output: Mapped[bool | None]
    image_input: Mapped[bool | None]
    reasoning: Mapped[bool | None]
    availability: Mapped[str | None] = mapped_column(String(40))
    __table_args__ = (UniqueConstraint("access_provider_id", "api_model_id", "variant"),)


class DeploymentAlias(Base):
    __tablename__ = "deployment_aliases"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column(String(900))
    deployment_id: Mapped[str] = mapped_column(ForeignKey("deployments.id"), index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("source_records.id"))
    __table_args__ = (UniqueConstraint("source_id", "external_id"),)


class Fact(Base):
    __tablename__ = "fact_observations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(300))
    field: Mapped[str] = mapped_column(String(100))
    value: Mapped[Any] = mapped_column(JSON)
    source_record_id: Mapped[str] = mapped_column(ForeignKey("source_records.id"))
    verification: Mapped[str] = mapped_column(String(40))
    authority: Mapped[int]
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index("ix_fact_entity_field", "entity_type", "entity_id", "field"),)


class CurrentFact(Base):
    __tablename__ = "current_facts"
    entity_type: Mapped[str] = mapped_column(String(30), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(300), primary_key=True)
    field: Mapped[str] = mapped_column(String(100), primary_key=True)
    observation_id: Mapped[str] = mapped_column(ForeignKey("fact_observations.id"))


class SourceClaim(Base):
    __tablename__ = "source_claims"
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(300), primary_key=True)
    field: Mapped[str] = mapped_column(String(100), primary_key=True)
    observation_id: Mapped[str] = mapped_column(ForeignKey("fact_observations.id"), index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirming_record_id: Mapped[str | None] = mapped_column(ForeignKey("source_records.id"))


class Price(Base):
    __tablename__ = "pricing_observations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    deployment_id: Mapped[str] = mapped_column(ForeignKey("deployments.id"), index=True)
    metric: Mapped[str] = mapped_column(String(60))
    amount: Mapped[Decimal] = mapped_column(Numeric(60, 30))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    quantity: Mapped[int] = mapped_column(default=1000000)
    unit: Mapped[str] = mapped_column(String(40), default="tokens")
    source_record_id: Mapped[str] = mapped_column(ForeignKey("source_records.id"))
    native_amount: Mapped[str] = mapped_column(String(100))
    native_quantity: Mapped[int]
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "amount >= 0 AND quantity > 0 AND native_quantity > 0", name="positive_price"
        ),
    )


class Conflict(Base):
    __tablename__ = "source_conflicts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(300), index=True)
    field: Mapped[str] = mapped_column(String(100))
    observation_a: Mapped[str] = mapped_column(ForeignKey("fact_observations.id"))
    observation_b: Mapped[str] = mapped_column(ForeignKey("fact_observations.id"))
    status: Mapped[str] = mapped_column(String(40), default="open")
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MarketEvent(Base):
    __tablename__ = "market_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(300), index=True)
    title: Mapped[str] = mapped_column(String(1000))
    old_value: Mapped[Any | None] = mapped_column(JSON)
    new_value: Mapped[Any | None] = mapped_column(JSON)
    source_record_id: Mapped[str] = mapped_column(ForeignKey("source_records.id"))
    importance: Mapped[str] = mapped_column(String(30), default="low")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class BenchmarkDefinition(Base):
    __tablename__ = "benchmark_definitions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    version: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(60))
    owner: Mapped[str | None] = mapped_column(String(300))
    higher_is_better: Mapped[bool | None]
    score_min: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    score_max: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    source_record_id: Mapped[str] = mapped_column(ForeignKey("source_records.id"))
    __table_args__ = (UniqueConstraint("name", "version"),)


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("models.id"), index=True)
    benchmark_id: Mapped[str] = mapped_column(ForeignKey("benchmark_definitions.id"), index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    verification: Mapped[str] = mapped_column(String(40))
    evaluator: Mapped[str] = mapped_column(String(300))
    source_record_id: Mapped[str] = mapped_column(ForeignKey("source_records.id"))
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    algorithm_version: Mapped[str] = mapped_column(String(40))
    request: Mapped[dict[str, Any]] = mapped_column(JSON)
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
