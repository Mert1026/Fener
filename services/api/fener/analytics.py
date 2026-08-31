"""Comparable benchmark evidence only; no guessed scales or task weights."""

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session


def normalize_score(score: Decimal, lower: Decimal, upper: Decimal, higher: bool) -> Decimal:
    if upper <= lower or not lower <= score <= upper:
        raise ValueError("Score must lie inside a nonempty documented scale")
    result = (score - lower) / (upper - lower)
    return result if higher else Decimal(1) - result


def comparable_scores(
    session: Session,
) -> tuple[dict[str, dict[str, Decimal]], list[dict[str, Any]]]:
    # AI-extracted claims remain unverified. They must never influence
    # recommendations or a quality frontier before a later review workflow.
    return {}, []
