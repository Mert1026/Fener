from decimal import Decimal

import pytest
from fener.analytics import comparable_scores, normalize_score


def test_normalization_preserves_direction_and_rejects_bad_scales():
    assert normalize_score(Decimal(75), Decimal(0), Decimal(100), True) == Decimal("0.75")
    assert normalize_score(Decimal(75), Decimal(0), Decimal(100), False) == Decimal("0.25")
    with pytest.raises(ValueError):
        normalize_score(Decimal(150), Decimal(0), Decimal(100), True)
    with pytest.raises(ValueError):
        normalize_score(Decimal(0), Decimal(0), Decimal(0), True)


def test_empty_evidence_never_generates_quality_frontier(client, session):
    assert comparable_scores(session) == ({}, [])
    response = client.post(
        "/api/v1/analytics/frontier", json={"weights": {"benchmark:missing": "1"}}
    )
    assert response.status_code == 200 and response.json()["points"] == []
