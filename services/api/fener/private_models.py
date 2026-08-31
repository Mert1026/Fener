"""Private user intelligence; never exposed through public catalog queries."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fener.db import Base, utcnow


class ResearchRun(Base):
    __tablename__ = "research_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    query: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(40), default="running")
    request: Mapped[dict[str, Any]] = mapped_column(JSON)
    report: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Harness(Base):
    __tablename__ = "harnesses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HarnessRole(Base):
    __tablename__ = "harness_roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    harness_id: Mapped[str] = mapped_column(ForeignKey("harnesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    default_deployment_id: Mapped[str | None] = mapped_column(ForeignKey("deployments.id"))
    __table_args__ = (UniqueConstraint("harness_id", "name"),)


class ModelPolicy(Base):
    __tablename__ = "model_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("harness_roles.id"), index=True)
    version: Mapped[int]
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_note: Mapped[str | None] = mapped_column(Text)
    approved_deployment_id: Mapped[str | None] = mapped_column(ForeignKey("deployments.id"))
    __table_args__ = (UniqueConstraint("role_id", "version"),)


class TelemetryRun(Base):
    __tablename__ = "harness_run_telemetry"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    external_run_id: Mapped[str] = mapped_column(String(200))
    harness_id: Mapped[str] = mapped_column(ForeignKey("harnesses.id"), index=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("harness_roles.id"), index=True)
    deployment_id: Mapped[str] = mapped_column(ForeignKey("deployments.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int]
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    cached_tokens: Mapped[int]
    cost: Mapped[Decimal | None] = mapped_column(Numeric(60, 30))
    success: Mapped[bool]
    retry_count: Mapped[int]
    error_category: Mapped[str | None] = mapped_column(String(100))
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    fingerprint: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint("harness_id", "external_run_id"),)


class EvaluationSuite(Base):
    __tablename__ = "evaluation_suites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("name", "version"),)


class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    suite_id: Mapped[str] = mapped_column(ForeignKey("evaluation_suites.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    input: Mapped[str] = mapped_column(Text)
    reference: Mapped[str] = mapped_column(Text)
    scorer: Mapped[str] = mapped_column(String(40))
    scorer_version: Mapped[str] = mapped_column(String(40), default="1")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    suite_id: Mapped[str] = mapped_column(ForeignKey("evaluation_suites.id"), index=True)
    deployment_id: Mapped[str] = mapped_column(ForeignKey("deployments.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    evaluator_version: Mapped[str] = mapped_column(String(100))
    score: Mapped[Decimal] = mapped_column(Numeric(10, 8))
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON)


class SyncRequest(Base):
    __tablename__ = "sync_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    active_source: Mapped[str | None] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingestion_run_id: Mapped[str | None] = mapped_column(ForeignKey("ingestion_runs.id"))


class IdentityOverride(Base):
    __tablename__ = "deployment_identity_overrides"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    deployment_id: Mapped[str] = mapped_column(ForeignKey("deployments.id"), index=True)
    previous_model_id: Mapped[str] = mapped_column(ForeignKey("models.id"))
    target_model_id: Mapped[str] = mapped_column(ForeignKey("models.id"))
    evidence_url: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
