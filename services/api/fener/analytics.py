"""Comparable benchmark evidence only; no guessed scales or task weights."""

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fener.models import BenchmarkDefinition, BenchmarkResult, SourceRecord


def normalize_score(score: Decimal, lower: Decimal, upper: Decimal, higher: bool) -> Decimal:
    if upper <= lower or not lower <= score <= upper:
        raise ValueError("Score must lie inside a nonempty documented scale")
    result = (score - lower) / (upper - lower)
    return result if higher else Decimal(1) - result


def comparable_scores(
    session: Session,
) -> tuple[dict[str, dict[str, Decimal]], list[dict[str, Any]]]:
    scores: dict[str, dict[str, Decimal]] = {}
    provenance = []
    seen: set[tuple[str, str]] = set()
    rows = session.execute(
        select(BenchmarkResult, BenchmarkDefinition, SourceRecord)
        .join(BenchmarkDefinition, BenchmarkResult.benchmark_id == BenchmarkDefinition.id)
        .join(SourceRecord, BenchmarkResult.source_record_id == SourceRecord.id)
        .where(
            BenchmarkDefinition.score_min.is_not(None),
            BenchmarkDefinition.score_max.is_not(None),
            BenchmarkDefinition.higher_is_better.is_not(None),
        )
        .order_by(SourceRecord.observed_at.desc(), BenchmarkResult.id)
    )
    for result, definition, record in rows:
        if (
            definition.version.startswith("unspecified:")
            or not definition.version
            or result.evaluator in {"", "Unspecified by catalog"}
        ):
            continue
        # Evaluators remain separate: the key includes an exact benchmark
        # version AND evaluator, preventing silent averaging across protocols.
        key = f"{definition.id}:{result.evaluator}"
        pair = (result.model_id, key)
        if pair in seen:
            continue
        seen.add(pair)
        assert definition.score_min is not None and definition.score_max is not None
        assert definition.higher_is_better is not None
        try:
            value = normalize_score(
                result.score,
                definition.score_min,
                definition.score_max,
                definition.higher_is_better,
            )
        except ValueError:
            continue
        scores.setdefault(result.model_id, {})[key] = value
        provenance.append(
            {
                "model_id": result.model_id,
                "metric": f"benchmark:{key}",
                "result_id": result.id,
                "benchmark_id": definition.id,
                "name": definition.name,
                "version": definition.version,
                "evaluator": result.evaluator,
                "normalized_score": str(value),
                "source": record.source_id,
                "source_url": record.source_url,
                "observed_at": record.observed_at.isoformat(),
                "verification": result.verification,
            }
        )
    return scores, provenance
