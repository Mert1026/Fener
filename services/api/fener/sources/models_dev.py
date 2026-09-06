from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from fener.sources.contracts import NativePrice, NormalizedRecord


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    limit: dict[str, int | None] = Field(default_factory=dict)
    cost: dict[str, Any] = Field(default_factory=dict)
    modalities: dict[str, list[str]] = Field(default_factory=dict)
    tool_call: bool | None = None
    reasoning: bool | None = None
    structured_output: bool | None = None


class CatalogProvider(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    doc: str | None = None
    models: dict[str, CatalogModel]


def capabilities(row: CatalogModel) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for field, value in [
        ("tool_calling", row.tool_call),
        ("reasoning", row.reasoning),
        ("structured_output", row.structured_output),
    ]:
        if value is not None:
            facts[field] = value
    for direction, modalities in row.modalities.items():
        for modality in modalities:
            facts[f"{modality}_{direction}"] = True
    for key, field in [("context", "context_window"), ("output", "max_output")]:
        limit_value = row.limit.get(key)
        if limit_value is not None:
            if limit_value < 0:
                raise ValueError("Token limits must be nonnegative")
            facts[field] = limit_value
    return facts


def normalize_models(payload: Any) -> list[NormalizedRecord]:
    parsed = TypeAdapter(dict[str, CatalogModel]).validate_python(payload)
    records = []
    for key, row in parsed.items():
        raw = payload[key]
        facts = capabilities(row)
        for field in [
            "description",
            "family",
            "release_date",
            "open_weights",
            "license",
            "knowledge",
        ]:
            if field in raw and raw[field] is not None:
                facts[field] = raw[field]
        records.append(
            NormalizedRecord(
                external_id=key,
                name=row.name,
                canonical_id=key,
                canonical=True,
                publisher_id=key.split("/")[0] if "/" in key else None,
                model_facts=facts,
                raw=raw,
            )
        )
    return records


def normalize(payload: Any) -> list[NormalizedRecord]:
    providers = TypeAdapter(dict[str, CatalogProvider]).validate_python(payload)
    records = []
    metrics = {
        "input": "input_tokens",
        "output": "output_tokens",
        "cache_read": "cached_input",
        "cache_write": "cache_write",
        "reasoning": "reasoning_tokens",
        "input_audio": "audio_input_tokens",
        "output_audio": "audio_output_tokens",
    }
    for provider_id, provider in providers.items():
        for model_id, row in provider.models.items():
            raw = payload[provider_id]["models"][model_id]
            hint = raw.get("base_model") or (
                model_id if "/" in model_id else f"{provider_id}/{model_id}"
            )
            prices = [
                NativePrice(metric=metric, amount=row.cost[key], quantity=1_000_000)
                for key, metric in metrics.items()
                if row.cost.get(key) is not None
            ]
            facts = capabilities(row)
            facts["availability"] = "deprecated" if raw.get("status") == "deprecated" else "listed"
            records.append(
                NormalizedRecord(
                    external_id=f"{provider_id}/{model_id}",
                    name=row.name,
                    canonical_id=hint,
                    provider_id=provider_id,
                    provider_name=provider.name,
                    provider_url=provider.doc,
                    api_id=model_id,
                    upstream_id=None,
                    listing_kind="routing_quote" if provider_id == "openrouter" else "deployment",
                    deployment_facts=facts,
                    prices=prices,
                    raw=raw,
                )
            )
    return records
