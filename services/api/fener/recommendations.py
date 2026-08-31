from decimal import Decimal, localcontext
from typing import Any

from pydantic import Field, model_validator

from fener.api_schemas import DeploymentView, StrictInput

ALGORITHM_VERSION = "flat-cost-evidence-v2"


class Workload(StrictInput):
    requests: int = Field(default=10000, ge=0, le=1_000_000_000)
    input_tokens: int = Field(default=2000, ge=0, le=100_000_000)
    output_tokens: int = Field(default=500, ge=0, le=100_000_000)
    cached_input_tokens: int = Field(default=0, ge=0)
    extra_usage: dict[str, Decimal] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_usage(self) -> "Workload":
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("Cached input is a subset of total input tokens")
        allowed = {
            "cache_write",
            "reasoning_tokens",
            "image",
            "search_call",
            "audio_input_tokens",
            "audio_output_tokens",
            "video_second",
            "audio_minute",
        }
        if any(
            k not in allowed or not v.is_finite() or v < 0 or v > 1_000_000_000
            for k, v in self.extra_usage.items()
        ):
            raise ValueError("Unsupported or invalid extra usage metric")
        return self


class RecommendationInput(StrictInput):
    task: str = Field(default="general", max_length=100)
    required_capabilities: list[str] = Field(default_factory=list, max_length=20)
    min_context: int = Field(default=0, ge=0)
    open_weights: bool = False
    providers: list[str] = Field(default_factory=list, max_length=30)
    budget: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    workload: Workload = Field(default_factory=Workload)
    weights: dict[str, Decimal] = Field(default_factory=lambda: {"price": Decimal(1)})
    allow_stale: bool = False
    allow_routing_quotes: bool = False
    allow_unresolved_models: bool = False
    allow_zero_metered_rates: bool = False
    limit: int = Field(default=10, ge=1, le=30)

    @model_validator(mode="after")
    def validate_weights(self) -> "RecommendationInput":
        if (
            not self.weights
            or any(not v.is_finite() or v < 0 for v in self.weights.values())
            or sum(self.weights.values()) <= 0
        ):
            raise ValueError("Weights must be finite, nonnegative and have a positive sum")
        if any(
            k not in {"price", "latency"} and not k.startswith("benchmark:") for k in self.weights
        ):
            raise ValueError("Use price, latency or benchmark:<versioned-benchmark-id> weights")
        return self


def estimate_cost(deployment: DeploymentView, workload: Workload) -> dict[str, Any]:
    with localcontext() as context:
        context.prec = 100
        return _estimate_cost(deployment, workload)


def _estimate_cost(deployment: DeploymentView, workload: Workload) -> dict[str, Any]:
    quantities = {
        "input_tokens": Decimal(workload.input_tokens - workload.cached_input_tokens),
        "output_tokens": Decimal(workload.output_tokens),
        "cached_input": Decimal(workload.cached_input_tokens),
        "request": Decimal(1),
        **workload.extra_usage,
    }
    parts = []
    missing = []
    total = Decimal(0)
    for metric, quantity in quantities.items():
        if quantity == 0 or workload.requests == 0:
            continue
        fact = deployment.facts.get(f"price.{metric}")
        if fact is None:
            # Request surcharge is optional; absence is disclosed, never treated as a universal free claim.
            if metric != "request":
                missing.append(metric)
            continue
        price = fact.value
        if price["currency"] != "USD":
            missing.append(f"{metric}: non-USD")
            continue
        amount = (
            Decimal(price["amount"]) * quantity * workload.requests / Decimal(price["quantity"])
        )
        total += amount
        parts.append(
            {
                "metric": metric,
                "usage_per_request": str(quantity),
                "amount": str(amount),
                "evidence_id": fact.id,
            }
        )
    return {
        "estimated_cost": str(total) if not missing else None,
        "currency": "USD",
        "components": parts,
        "missing": missing,
        "assumptions": [
            "Flat listed rates; taxes, purchase fees, unlisted surcharges and tier changes excluded.",
            "Zero metered rates can require a paid plan, trial credits or quotas; they do not guarantee unlimited free service.",
            "Cached input is subtracted from total input; extra reasoning usage must not also be counted as output.",
            *(
                ["Marketplace routing quote; selected endpoint can cost more."]
                if deployment.listing_kind == "routing_quote"
                else []
            ),
        ],
    }


def pareto_ids(points: list[tuple[str, Decimal, Decimal]]) -> set[str]:
    return {
        id
        for id, cost, quality in points
        if not any(
            other_cost <= cost
            and other_quality >= quality
            and (other_cost < cost or other_quality > quality)
            for other_id, other_cost, other_quality in points
            if other_id != id
        )
    }


def recommend(
    deployments: list[DeploymentView],
    request: RecommendationInput,
    model_facts: dict[str, dict[str, Any]],
    benchmarks: dict[str, dict[str, Decimal]] | None = None,
) -> dict[str, Any]:
    benchmarks = benchmarks or {}
    eligible = []
    rejected = []
    for deployment in deployments:
        reasons = []
        facts = deployment.facts
        if deployment.identity_status != "resolved" and not request.allow_unresolved_models:
            reasons.append("Canonical model identity is unresolved")
        if request.providers and deployment.access_provider not in request.providers:
            reasons.append("Provider is excluded")
        if deployment.listing_kind == "routing_quote" and not request.allow_routing_quotes:
            reasons.append("Unbound marketplace routing quote")
        if facts.get("availability") is None or facts["availability"].value not in {
            "available",
            "listed",
        }:
            reasons.append("Availability is unknown or unavailable")
        for capability in request.required_capabilities:
            fact = facts.get(capability)
            if fact is None or fact.value is not True:
                reasons.append(f"Required {capability} is not confirmed")
        context = facts.get("context_window")
        required_context = max(
            request.min_context, request.workload.input_tokens + request.workload.output_tokens
        )
        if required_context and (context is None or context.value < required_context):
            reasons.append("Required serving context is not confirmed")
        max_output = facts.get("max_output")
        if request.workload.output_tokens and max_output is None:
            reasons.append("Serving output limit is not confirmed")
        if max_output is not None and max_output.value < request.workload.output_tokens:
            reasons.append("Output exceeds serving limit")
        if (
            request.open_weights
            and model_facts.get(deployment.model_id, {}).get("open_weights") is not True
        ):
            reasons.append("Open weights are not confirmed")
        relevant = [
            v
            for k, v in facts.items()
            if k.startswith("price.")
            or k in {"availability", "context_window", *request.required_capabilities}
        ]
        if not request.allow_stale and any(v.stale for v in relevant):
            reasons.append("Required evidence is stale")
        cost = estimate_cost(deployment, request.workload)
        if cost["estimated_cost"] is None:
            reasons.append("Missing prices: " + ", ".join(cost["missing"]))
        elif request.budget is not None and Decimal(cost["estimated_cost"]) > request.budget:
            reasons.append("Monthly budget exceeded")
        elif (
            not request.allow_zero_metered_rates
            and request.workload.requests > 0
            and Decimal(cost["estimated_cost"]) == 0
        ):
            reasons.append(
                "Zero metered rate requires explicit opt-in; plan fees and quotas may apply"
            )
        if reasons:
            rejected.append(
                {
                    "deployment_id": deployment.id,
                    "model_name": deployment.model_name,
                    "reasons": reasons,
                }
            )
        else:
            eligible.append((deployment, cost))
    max_cost = max((Decimal(cost["estimated_cost"]) for _, cost in eligible), default=Decimal(0))
    ranked = []
    for deployment, cost in eligible:
        values: dict[str, Decimal] = {
            "price": Decimal(1) - Decimal(cost["estimated_cost"]) / max_cost
            if max_cost
            else Decimal(1)
        }
        ttft = deployment.facts.get("ttft_seconds")
        if ttft is not None and Decimal(str(ttft.value)) >= 0:
            values["latency"] = Decimal(1) / (Decimal(1) + Decimal(str(ttft.value)))
        values.update(
            {
                f"benchmark:{key}": value
                for key, value in benchmarks.get(deployment.model_id, {}).items()
            }
        )
        total_weight = sum(request.weights.values())
        covered = sum(weight for key, weight in request.weights.items() if key in values)
        score = (
            sum(weight * values[key] for key, weight in request.weights.items() if key in values)
            / total_weight
        )
        missing = [key for key, weight in request.weights.items() if weight and key not in values]
        ranked.append(
            {
                "deployment": deployment.model_dump(mode="json"),
                **cost,
                "score": str(score),
                "coverage": str(covered / total_weight),
                "confidence": "low"
                if missing or not any(k.startswith("benchmark:") for k in request.weights)
                else "moderate",
                "missing_evidence": missing,
                "breakdown": {k: str(v) for k, v in values.items() if k in request.weights},
                "reason": "Satisfies confirmed requirements; ranked using available weighted evidence. Missing weights contribute no score.",
            }
        )
    ranked.sort(
        key=lambda row: (
            -Decimal(row["score"]),
            Decimal(row["estimated_cost"]),
            row["deployment"]["id"],
        )
    )
    usable = [row for row in ranked if Decimal(row["coverage"]) > 0]
    selected = usable[: request.limit]
    primary = selected[0] if selected else None
    fallbacks = sorted(
        usable[1:],
        key=lambda row: (
            row["deployment"]["model_id"] != primary["deployment"]["model_id"] if primary else True,
            -Decimal(row["score"]),
        ),
    )[:3]
    return {
        "algorithm_version": ALGORITHM_VERSION,
        "recommended": primary,
        "alternatives": selected[1:],
        "fallback_chain": fallbacks,
        "eligible_count": len(eligible),
        "rejected_count": len(rejected),
        "rejected": rejected[:100],
        "warnings": [
            "This is an evidence-limited recommendation, not a universal model ranking.",
            "Unknown benchmark methodology is excluded; current catalog benchmark entries may not support quality scoring.",
        ],
    }
