"""Persist only cited Z.ai benchmark candidates, isolated from source-ingested facts."""

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fener.evidence import digest
from fener.models import Model, ResearchBenchmark


def persist_research_benchmarks(
    session: Session,
    candidates: list[dict[str, Any]],
    *,
    research_run_id: str | None = None,
    refresh_item_id: str | None = None,
) -> dict[str, Any]:
    if (research_run_id is None) == (refresh_item_id is None):
        raise ValueError("Exactly one benchmark research origin is required")
    by_name: dict[str, list[Model]] = {}
    for model in session.scalars(select(Model)):
        by_name.setdefault(model.name.casefold().strip(), []).append(model)

    imported, skipped = 0, []
    for index, candidate in enumerate(candidates):
        matches = by_name.get(candidate["model_name"].casefold().strip(), [])
        if len(matches) != 1:
            skipped.append(
                {
                    "model_name": candidate["model_name"],
                    "reason": "No unique exact catalog model-name match",
                }
            )
            continue
        model = matches[0]
        origin = research_run_id or refresh_item_id
        row_id = digest("ai-research-benchmark", origin, index, candidate)
        if session.get(ResearchBenchmark, row_id) is not None:
            continue
        session.add(
            ResearchBenchmark(
                id=row_id,
                research_run_id=research_run_id,
                refresh_item_id=refresh_item_id,
                model_id=model.id,
                name=candidate["name"],
                version=candidate["version"],
                category=candidate["category"],
                metric=candidate["metric"],
                score=Decimal(candidate["score"]),
                evaluator=candidate["evaluator"],
                source_url=candidate["source_url"],
                source_title=candidate["source_title"],
                reported_date=candidate.get("reported_date"),
                higher_is_better=candidate.get("higher_is_better"),
                score_min=(
                    Decimal(candidate["score_min"])
                    if candidate.get("score_min") is not None
                    else None
                ),
                score_max=(
                    Decimal(candidate["score_max"])
                    if candidate.get("score_max") is not None
                    else None
                ),
            )
        )
        imported += 1
    return {"imported": imported, "skipped": skipped}
