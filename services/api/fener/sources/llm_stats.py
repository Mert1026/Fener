"""Authenticated catalog contract documented at llm-stats.com/developer.

Benchmark detail ingestion is gated until the authenticated schema can be verified.
Category 'top_scores' are NOT silently converted to benchmark results.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

from fener.sources.contracts import NormalizedRecord


class Organization(BaseModel):
    id: str
    name: str


class Entry(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    organization: Organization


class Catalog(BaseModel):
    models: list[Entry]
    next_cursor: str | None = None
    total: int


def normalize(payload: Any) -> list[NormalizedRecord]:
    catalog = Catalog.model_validate(payload)
    return [
        NormalizedRecord(
            external_id=row.id,
            name=row.name,
            canonical_id=f"{row.organization.id}/{row.id}",
            publisher_id=row.organization.id,
            raw=raw,
        )
        for row, raw in zip(catalog.models, payload["models"], strict=True)
    ]
