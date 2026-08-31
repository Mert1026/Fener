from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvidenceView(BaseModel):
    id: str
    value: Any
    source: str
    source_url: str
    observed_at: datetime
    last_seen_at: datetime
    verification: str
    stale: bool


class ModelView(BaseModel):
    id: str
    name: str
    publisher: str | None
    family: str | None
    context_window: int | None
    open_weights: bool | None
    release_date: str | None
    identity_status: str
    deployment_count: int
    input_price_from: str | None
    output_price_from: str | None
    input_price_evidence: EvidenceView | None = None
    output_price_evidence: EvidenceView | None = None
    capabilities: list[str]
    facts: dict[str, EvidenceView]


class ModelPage(BaseModel):
    items: list[ModelView]
    total: int
    offset: int
    limit: int


class DeploymentView(BaseModel):
    id: str
    model_id: str
    model_name: str
    access_provider: str
    upstream_provider: str | None
    api_model_id: str
    variant: str
    listing_kind: str
    facts: dict[str, EvidenceView]


class ProviderView(BaseModel):
    id: str
    name: str
    kind: str
    deployment_count: int
    facts: dict[str, EvidenceView]


class ModelDetail(BaseModel):
    model: ModelView
    deployments: list[DeploymentView]
    benchmarks: list[dict[str, Any]]


class ApiError(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompareInput(StrictInput):
    ids: list[str] = Field(min_length=2, max_length=6)
