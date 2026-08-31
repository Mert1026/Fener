from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fener.api_schemas import StrictInput
from fener.db import session_dependency, utcnow
from fener.evidence import digest
from fener.models import Deployment
from fener.private_models import (
    EvaluationCase,
    EvaluationRun,
    EvaluationSuite,
    Harness,
    HarnessRole,
    ModelPolicy,
    TelemetryRun,
)
from fener.recommendations import RecommendationInput
from fener.security import require_admin

router = APIRouter(
    prefix="/api/v1", dependencies=[Depends(require_admin)], tags=["Private intelligence"]
)
DB = Annotated[Session, Depends(session_dependency)]


class HarnessInput(StrictInput):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    roles: list[str] = Field(
        default_factory=lambda: ["researcher", "coder", "reviewer", "router"],
        min_length=1,
        max_length=20,
    )

    @model_validator(mode="after")
    def unique_roles(self) -> "HarnessInput":
        if len(set(self.roles)) != len(self.roles) or any(
            not role or len(role) > 100 for role in self.roles
        ):
            raise ValueError("Role names must be unique and between 1 and 100 characters")
        return self


@router.post("/harnesses", status_code=201)
def create_harness(request: HarnessInput, session: DB) -> dict[str, str]:
    if session.scalar(select(Harness.id).where(Harness.name == request.name)):
        raise HTTPException(409, "A harness with this name already exists")
    harness = Harness(id=str(uuid4()), name=request.name, description=request.description)
    session.add(harness)
    session.flush()
    session.add_all(
        [HarnessRole(id=str(uuid4()), harness_id=harness.id, name=role) for role in request.roles]
    )
    session.commit()
    return {"id": harness.id}


@router.get("/harnesses")
def harnesses(session: DB) -> list[dict[str, Any]]:
    result = []
    for harness in session.scalars(select(Harness).order_by(Harness.created_at)):
        aggregate = session.execute(
            select(
                func.count(), func.sum(TelemetryRun.cost), func.avg(TelemetryRun.duration_ms)
            ).where(TelemetryRun.harness_id == harness.id)
        ).one()
        success_count = (
            session.scalar(
                select(func.count())
                .select_from(TelemetryRun)
                .where(TelemetryRun.harness_id == harness.id, TelemetryRun.success.is_(True))
            )
            or 0
        )
        roles = session.scalars(select(HarnessRole).where(HarnessRole.harness_id == harness.id))
        result.append(
            {
                "id": harness.id,
                "name": harness.name,
                "description": harness.description,
                "runs": aggregate[0],
                "observed_spend": str(aggregate[1]) if aggregate[1] is not None else None,
                "mean_duration_ms": aggregate[2],
                "success_rate": success_count / aggregate[0] if aggregate[0] else None,
                "roles": [
                    {"id": r.id, "name": r.name, "default_deployment_id": r.default_deployment_id}
                    for r in roles
                ],
            }
        )
    return result


@router.post("/harnesses/roles/{role_id}/policies", status_code=201)
def create_policy(role_id: str, request: RecommendationInput, session: DB) -> dict[str, Any]:
    role = session.scalar(select(HarnessRole).where(HarnessRole.id == role_id).with_for_update())
    if not role:
        raise HTTPException(404, "Role not found")
    version = (
        session.scalar(select(func.max(ModelPolicy.version)).where(ModelPolicy.role_id == role_id))
        or 0
    ) + 1
    policy = ModelPolicy(
        id=str(uuid4()),
        role_id=role_id,
        version=version,
        configuration=request.model_dump(mode="json"),
    )
    session.add(policy)
    session.commit()
    return {"id": policy.id, "version": version, "status": "draft"}


class PolicyApproval(StrictInput):
    approve: Literal[True]
    deployment_id: str
    note: str = Field(min_length=3, max_length=2000)


@router.post("/harnesses/policies/{policy_id}/approve")
def approve_policy(policy_id: str, request: PolicyApproval, session: DB) -> dict[str, str]:
    policy = session.scalar(
        select(ModelPolicy).where(ModelPolicy.id == policy_id).with_for_update()
    )
    if not policy:
        raise HTTPException(404, "Policy not found")
    if policy.approved_at:
        raise HTTPException(409, "This policy version is already approved; create a new version")
    if not session.get(Deployment, request.deployment_id):
        raise HTTPException(404, "Deployment not found")
    # An explicit human-approved operation, never called by recommendations or ingestion.
    role = session.get(HarnessRole, policy.role_id)
    assert role is not None
    role.default_deployment_id = request.deployment_id
    policy.approved_at = utcnow()
    policy.approval_note = request.note
    session.commit()
    return {"status": "approved"}


class TelemetryInput(StrictInput):
    external_run_id: str = Field(min_length=1, max_length=200)
    harness_id: str
    role_id: str
    deployment_id: str
    task_type: str = Field(max_length=100)
    started_at: AwareDatetime
    duration_ms: int = Field(ge=0, le=604800000)
    input_tokens: int = Field(ge=0, le=1_000_000_000)
    output_tokens: int = Field(ge=0, le=1_000_000_000)
    cached_tokens: int = Field(default=0, ge=0)
    cost: Decimal | None = Field(
        default=None, ge=0, allow_inf_nan=False, max_digits=60, decimal_places=30
    )
    success: bool
    retry_count: int = Field(default=0, ge=0, le=1000)
    error_category: str | None = Field(default=None, max_length=100)
    quality_score: Decimal | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def cached_subset(self) -> "TelemetryInput":
        if self.cached_tokens > self.input_tokens:
            raise ValueError("Cached tokens cannot exceed input tokens")
        return self


@router.post("/telemetry/runs", status_code=201)
def telemetry(request: TelemetryInput, session: DB) -> dict[str, Any]:
    role = session.get(HarnessRole, request.role_id)
    if not role or role.harness_id != request.harness_id:
        raise HTTPException(422, "Role does not belong to this harness")
    if not session.get(Deployment, request.deployment_id):
        raise HTTPException(422, "Unknown deployment")
    fingerprint = digest(request.model_dump(mode="json"))
    previous = session.scalar(
        select(TelemetryRun).where(
            TelemetryRun.harness_id == request.harness_id,
            TelemetryRun.external_run_id == request.external_run_id,
        )
    )
    if previous:
        if previous.fingerprint != fingerprint:
            raise HTTPException(409, "Run identifier was already used with different telemetry")
        return {"id": previous.id, "duplicate": True}
    row = TelemetryRun(id=str(uuid4()), fingerprint=fingerprint, **request.model_dump())
    session.add(row)
    session.commit()
    return {"id": row.id, "duplicate": False}


@router.get("/telemetry/runs")
def telemetry_runs(session: DB, limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    return [
        {
            "id": r.id,
            "harness_id": r.harness_id,
            "deployment_id": r.deployment_id,
            "task_type": r.task_type,
            "started_at": r.started_at,
            "duration_ms": r.duration_ms,
            "success": r.success,
            "cost": str(r.cost) if r.cost is not None else None,
        }
        for r in session.scalars(
            select(TelemetryRun).order_by(TelemetryRun.started_at.desc()).limit(limit)
        )
    ]


class CaseInput(StrictInput):
    name: str = Field(min_length=1, max_length=200)
    input: str = Field(max_length=10000)
    reference: str = Field(min_length=1, max_length=10000)
    scorer: Literal["exact_match", "contains", "human"] = "exact_match"


class SuiteInput(StrictInput):
    name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    category: str = Field(default="general", max_length=100)
    cases: list[CaseInput] = Field(min_length=1, max_length=100)


@router.post("/evaluations/suites", status_code=201)
def create_suite(request: SuiteInput, session: DB) -> dict[str, str]:
    if session.scalar(
        select(EvaluationSuite.id).where(
            EvaluationSuite.name == request.name, EvaluationSuite.version == request.version
        )
    ):
        raise HTTPException(409, "Suite version already exists; create a new version")
    suite = EvaluationSuite(
        id=str(uuid4()), name=request.name, version=request.version, category=request.category
    )
    session.add(suite)
    session.flush()
    session.add_all(
        [
            EvaluationCase(
                id=str(uuid4()), suite_id=suite.id, scorer_version="1", **case.model_dump()
            )
            for case in request.cases
        ]
    )
    session.commit()
    return {"id": suite.id}


@router.get("/evaluations")
def evaluations(session: DB) -> dict[str, Any]:
    suites = []
    for suite in session.scalars(
        select(EvaluationSuite).order_by(EvaluationSuite.created_at.desc())
    ):
        cases = session.scalars(select(EvaluationCase).where(EvaluationCase.suite_id == suite.id))
        suites.append(
            {
                "id": suite.id,
                "name": suite.name,
                "version": suite.version,
                "category": suite.category,
                "cases": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "input": c.input,
                        "reference": c.reference,
                        "scorer": c.scorer,
                        "scorer_version": c.scorer_version,
                    }
                    for c in cases
                ],
            }
        )
    runs = [
        {
            "id": r.id,
            "suite_id": r.suite_id,
            "deployment_id": r.deployment_id,
            "score": str(r.score),
            "created_at": r.created_at,
            "evaluator_version": r.evaluator_version,
            "results": r.results,
        }
        for r in session.scalars(
            select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(100)
        )
    ]
    return {"suites": suites, "runs": runs}


class CaseResult(StrictInput):
    case_id: str
    output: str = Field(max_length=10000)
    human_score: Decimal | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)


class EvaluationInput(StrictInput):
    suite_id: str
    deployment_id: str
    outputs: list[CaseResult] = Field(min_length=1, max_length=100)
    evaluator_version: str = Field(min_length=1, max_length=100)


@router.post("/evaluations/runs", status_code=201)
def evaluate(request: EvaluationInput, session: DB) -> dict[str, str]:
    if not session.get(Deployment, request.deployment_id):
        raise HTTPException(422, "Unknown deployment")
    cases = list(
        session.scalars(select(EvaluationCase).where(EvaluationCase.suite_id == request.suite_id))
    )
    outputs = {row.case_id: row for row in request.outputs}
    if not cases or len(outputs) != len(request.outputs) or set(outputs) != {c.id for c in cases}:
        raise HTTPException(422, "Provide exactly one output for every case in this suite version")
    results = []
    for case in cases:
        output = outputs[case.id]
        if case.scorer == "human":
            if output.human_score is None:
                raise HTTPException(422, "Human-scored cases require an explicit human score")
            score = output.human_score
        else:
            matched = (
                output.output == case.reference
                if case.scorer == "exact_match"
                else case.reference in output.output
            )
            score = Decimal(int(matched))
        results.append(
            {
                "case_id": case.id,
                "score": str(score),
                "scorer": case.scorer,
                "scorer_version": case.scorer_version,
                "output": output.output,
            }
        )
    score = sum((Decimal(row["score"]) for row in results), Decimal(0)) / Decimal(len(results))
    row = EvaluationRun(
        id=str(uuid4()),
        suite_id=request.suite_id,
        deployment_id=request.deployment_id,
        evaluator_version=request.evaluator_version,
        score=score,
        results=results,
        configuration={"suite_id": request.suite_id, "engine": "deterministic-v1"},
    )
    session.add(row)
    session.commit()
    return {"id": row.id, "score": str(score)}
