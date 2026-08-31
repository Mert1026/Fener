"""Semantic comparisons without rounding source prices or rewriting evidence."""

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any


def equal_prices(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return bool(left == right)
    required = {"amount", "quantity", "currency", "unit"}
    if not required <= left.keys() or not required <= right.keys():
        return bool(left == right)
    if {k: v for k, v in left.items() if k not in {"amount", "quantity"}} != {
        k: v for k, v in right.items() if k not in {"amount", "quantity"}
    }:
        return False
    try:
        a, b, aq, bq = [
            Decimal(str(v))
            for v in (left["amount"], right["amount"], left["quantity"], right["quantity"])
        ]
        if not all(v.is_finite() for v in (a, b, aq, bq)) or aq <= 0 or bq <= 0:
            return False
        with localcontext() as context:
            context.prec = max(100, sum(len(v.as_tuple().digits) for v in (a, b, aq, bq)) + 4)
            return a * bq == b * aq
    except (InvalidOperation, ValueError, TypeError):
        return False


def equal_values(field: str, left: Any, right: Any) -> bool:
    return equal_prices(left, right) if field.startswith("price.") else left == right
