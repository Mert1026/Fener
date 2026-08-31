from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NativePrice(BaseModel):
    metric: str
    amount: Decimal = Field(ge=0, allow_inf_nan=False, max_digits=60, decimal_places=30)
    quantity: int = Field(gt=0)
    unit: str = "tokens"

    @property
    def normalized(self) -> Decimal:
        return self.amount * Decimal(1_000_000 if self.unit == "tokens" else 1) / self.quantity


class NormalizedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: str
    name: str
    canonical_id: str | None = None
    publisher_id: str | None = None
    canonical: bool = False
    provider_id: str | None = None
    provider_name: str | None = None
    provider_url: str | None = None
    upstream_id: str | None = None
    api_id: str | None = None
    variant: str = "default"
    listing_kind: str = "deployment"
    model_facts: dict[str, Any] = Field(default_factory=dict)
    deployment_facts: dict[str, Any] = Field(default_factory=dict)
    prices: list[NativePrice] = Field(default_factory=list)
    benchmarks: list[dict[str, Any]] = Field(default_factory=list)
    raw: dict[str, Any]


class SourceContractError(ValueError):
    """A source no longer conforms to the verified contract."""
