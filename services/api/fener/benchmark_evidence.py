"""Recover metric/report provenance and reject incomparable benchmark scales."""

from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit

from fener.evidence import digest
from fener.models import BenchmarkDefinition, BenchmarkResult, SourceRecord


def safe_report_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        return (
            value
            if parsed.scheme in {"http", "https"} and parsed.hostname and parsed.username is None
            else None
        )
    except ValueError:
        return None


def benchmark_metadata(
    result: BenchmarkResult, definition: BenchmarkDefinition, record: SourceRecord
) -> dict[str, Any]:
    matches = []
    for raw in record.raw.get("benchmarks", []):
        if not isinstance(raw, dict) or raw.get("name") != definition.name:
            continue
        try:
            if Decimal(str(raw.get("score"))) == result.score:
                matches.append(raw)
        except (InvalidOperation, ValueError):
            continue
    # Ambiguous source entries must not lend each other units or report links.
    raw = matches[0] if len(matches) == 1 else {}
    raw_metric = raw.get("metric")
    metric = (
        raw_metric.strip()
        if isinstance(raw_metric, str) and raw_metric.strip()
        else "Unspecified metric"
    )
    issues = []
    if metric == "Unspecified metric":
        issues.append("Score unit or metric not supplied")
    if not definition.version or definition.version.startswith("unspecified:"):
        issues.append("Benchmark version not supplied")
    if result.evaluator in {"", "Unspecified by catalog"}:
        issues.append("Evaluator/protocol not supplied")
    lower, upper = definition.score_min, definition.score_max
    if lower is None or upper is None or upper <= lower:
        issues.append("Documented numeric scale not supplied")
    elif not lower <= result.score <= upper:
        issues.append("Score falls outside the documented scale")
    if definition.higher_is_better is None:
        issues.append("Score direction not supplied")
    return {
        "metric": metric,
        "group_id": digest(definition.name.casefold().strip(), metric.casefold()),
        "report_url": safe_report_url(raw.get("source")),
        "reported_date": str(raw["date"]) if raw.get("date") else None,
        "quality_issues": issues,
        "comparable": not issues,
    }
