from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fener.api_schemas import DeploymentView, EvidenceView
from fener.recommendations import (
    RecommendationInput,
    Workload,
    estimate_cost,
    pareto_ids,
    recommend,
)
from pydantic import ValidationError


def candidate(id="a", input_price="1", output_price="3", tool=True):
    def fact(value):
        return EvidenceView(
            id="e",
            value=value,
            source="test",
            source_url="https://example.com",
            observed_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            verification="official",
            stale=False,
        )

    return DeploymentView(
        id=id,
        model_id=id,
        model_name=id,
        identity_status="resolved",
        access_provider="direct",
        upstream_provider="direct",
        api_model_id=id,
        variant="default",
        listing_kind="deployment",
        facts={
            "availability": fact("available"),
            "context_window": fact(200000),
            "max_output": fact(16000),
            "tool_calling": fact(tool),
            "price.input_tokens": fact(
                {"amount": input_price, "currency": "USD", "quantity": 1000000, "unit": "tokens"}
            ),
            "price.output_tokens": fact(
                {"amount": output_price, "currency": "USD", "quantity": 1000000, "unit": "tokens"}
            ),
            "price.cached_input": fact(
                {"amount": "0.1", "currency": "USD", "quantity": 1000000, "unit": "tokens"}
            ),
        },
    )


def test_cached_input_is_not_double_charged():
    result = estimate_cost(
        candidate(),
        Workload(requests=1000, input_tokens=2000, cached_input_tokens=1000, output_tokens=100),
    )
    assert Decimal(result["estimated_cost"]) == Decimal("1.4")


def test_missing_price_is_not_free():
    row = candidate()
    del row.facts["price.output_tokens"]
    assert estimate_cost(row, Workload())["estimated_cost"] is None


def test_constraints_budget_and_fallbacks():
    result = recommend(
        [
            candidate("cheap", "0.1", "0.1"),
            candidate("bad-tools", tool=False),
            candidate("expensive", "100", "100"),
        ],
        RecommendationInput(required_capabilities=["tool_calling"], budget=Decimal(20)),
        {},
    )
    assert result["recommended"]["deployment"]["id"] == "cheap"
    assert result["fallback_chain"] == []
    assert result["rejected_count"] == 2


def test_unknown_context_cannot_pass_requirement():
    row = candidate()
    del row.facts["context_window"]
    assert recommend([row], RecommendationInput(min_context=100000), {})["recommended"] is None


def test_missing_quality_is_explicit_and_cannot_create_score():
    result = recommend(
        [candidate()], RecommendationInput(weights={"benchmark:unavailable": Decimal(1)}), {}
    )
    assert result["recommended"] is None


def test_pareto_strict_dominance_and_ties():
    points = [
        ("a", Decimal(1), Decimal(8)),
        ("b", Decimal(2), Decimal(7)),
        ("c", Decimal(2), Decimal(9)),
        ("tie", Decimal(1), Decimal(8)),
    ]
    assert pareto_ids(points) == {"a", "c", "tie"}


def test_workload_validation():
    with pytest.raises(ValidationError):
        Workload(input_tokens=10, cached_input_tokens=11)
    with pytest.raises(ValidationError):
        Workload(extra_usage={"image": Decimal("NaN")})


def test_zero_metered_rates_and_unresolved_identities_require_opt_in():
    free = candidate(input_price="0", output_price="0")
    assert recommend([free], RecommendationInput(), {})["recommended"] is None
    assert (
        recommend([free], RecommendationInput(allow_zero_metered_rates=True), {})["recommended"]
        is not None
    )
    unknown = candidate()
    unknown.identity_status = "unresolved"
    assert recommend([unknown], RecommendationInput(), {})["recommended"] is None
    assert (
        recommend([unknown], RecommendationInput(allow_unresolved_models=True), {})["recommended"]
        is not None
    )
