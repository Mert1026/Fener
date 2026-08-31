from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fener.sources.contracts import NativePrice, NormalizedRecord


class RouterModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    pricing: dict[str, Any]
    context_length: int | None = Field(default=None, ge=0)
    architecture: dict[str, Any] = Field(default_factory=dict)
    supported_parameters: list[str] | None = None
    top_provider: dict[str, Any] | None = None


class Catalog(BaseModel):
    data: list[RouterModel]


def prices(values: dict[str, Any]) -> list[NativePrice]:
    metrics = {
        "prompt": "input_tokens",
        "completion": "output_tokens",
        "input_cache_read": "cached_input",
        "input_cache_write": "cache_write",
        "internal_reasoning": "reasoning_tokens",
        "request": "request",
        "image": "image",
        "web_search": "search_call",
    }
    return [
        NativePrice(
            metric=metric,
            amount=values[key],
            quantity=1,
            unit="tokens" if metric not in {"request", "image", "search_call"} else metric,
        )
        for key, metric in metrics.items()
        if values.get(key) is not None and str(values[key]) != "-1"
    ]


def capabilities(parameters: list[str] | None) -> dict[str, Any]:
    if parameters is None:
        return {}
    return {
        "tool_calling": "tools" in parameters,
        "structured_output": "structured_outputs" in parameters,
        "reasoning": "reasoning" in parameters,
    }


def normalize(payload: Any) -> list[NormalizedRecord]:
    catalog = Catalog.model_validate(payload)
    records = []
    for row, raw in zip(catalog.data, payload["data"], strict=True):
        facts = capabilities(row.supported_parameters)
        if row.context_length is not None:
            facts["context_window"] = row.context_length
        for direction in ("input", "output"):
            for modality in row.architecture.get(f"{direction}_modalities", []):
                facts[f"{modality}_{direction}"] = True
        if row.top_provider and row.top_provider.get("max_completion_tokens") is not None:
            facts["max_output"] = row.top_provider["max_completion_tokens"]
        facts["availability"] = "listed"
        records.append(
            NormalizedRecord(
                external_id=row.id,
                name=row.name,
                canonical_id=row.id,
                provider_id="openrouter",
                provider_name="OpenRouter",
                api_id=row.id,
                listing_kind="routing_quote",
                deployment_facts=facts,
                prices=prices(row.pricing),
                raw=raw,
            )
        )
    return records


class Endpoint(BaseModel):
    model_config = ConfigDict(extra="allow")
    provider_name: str
    tag: str
    name: str
    pricing: dict[str, Any]
    context_length: int | None = Field(default=None, ge=0)
    max_completion_tokens: int | None = Field(default=None, ge=0)
    supported_parameters: list[str] | None = None
    status: int | None = None


class EndpointData(BaseModel):
    id: str
    name: str
    endpoints: list[Endpoint]


class EndpointCatalog(BaseModel):
    data: EndpointData


def normalize_endpoints(payload: Any) -> list[NormalizedRecord]:
    data = EndpointCatalog.model_validate(payload).data
    records = []
    for endpoint, raw in zip(data.endpoints, payload["data"]["endpoints"], strict=True):
        facts = capabilities(endpoint.supported_parameters)
        for field, value in [
            ("context_window", endpoint.context_length),
            ("max_output", endpoint.max_completion_tokens),
        ]:
            if value is not None:
                facts[field] = value
        # Preserve the native status; do not guess undocumented negative status meanings.
        facts["availability"] = "available" if endpoint.status == 0 else "unknown"
        for field, key in [
            ("ttft_seconds", "latency_last_30m"),
            ("throughput_tps", "throughput_last_30m"),
        ]:
            if isinstance(raw.get(key), dict) and raw[key].get("p50") is not None:
                facts[field] = raw[key]["p50"]
        if raw.get("uptime_last_1d") is not None:
            facts["uptime_1d_percent"] = raw["uptime_last_1d"]
        records.append(
            NormalizedRecord(
                external_id=f"{data.id}#{endpoint.tag}",
                name=data.name,
                canonical_id=data.id,
                provider_id="openrouter",
                provider_name="OpenRouter",
                api_id=data.id,
                upstream_id=endpoint.provider_name,
                variant=endpoint.tag,
                deployment_facts=facts,
                prices=prices(endpoint.pricing),
                raw=raw,
            )
        )
    return records
