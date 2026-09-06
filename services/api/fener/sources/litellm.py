from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from fener.sources.contracts import NativePrice, NormalizedRecord

# For a first-party OpenAI deployment, the access provider namespace and API
# model ID identify the model exactly. This resolves identity only; LiteLLM's
# prices and capabilities remain aggregated evidence with their normal source
# authority in CatalogWriter.
DIRECT_MODEL_PUBLISHERS = {"openai"}


class Entry(BaseModel):
    model_config = ConfigDict(extra="allow")
    litellm_provider: str | None = None
    mode: str | None = None
    max_input_tokens: int | None = Field(default=None, ge=0)
    max_output_tokens: int | None = Field(default=None, ge=0)


def normalize(payload: Any) -> list[NormalizedRecord]:
    rows = TypeAdapter(dict[str, dict[str, Any]]).validate_python(payload)
    records = []
    for external_id, raw in rows.items():
        if external_id == "sample_spec":
            continue
        row = Entry.model_validate(raw)
        if not row.litellm_provider or row.mode != "chat":
            continue
        provider = row.litellm_provider
        # Only strip a literal provider prefix, never a model variant or dated suffix.
        api_id = external_id.removeprefix(provider + "/")
        hint = api_id if "/" in api_id else f"{provider}/{api_id}"
        facts: dict[str, Any] = {}
        for field, key in [
            ("tool_calling", "supports_function_calling"),
            ("parallel_tool_calling", "supports_parallel_function_calling"),
            ("structured_output", "supports_response_schema"),
            ("image_input", "supports_vision"),
            ("reasoning", "supports_reasoning"),
            ("prompt_caching", "supports_prompt_caching"),
        ]:
            if key in raw:
                if not isinstance(raw[key], bool):
                    raise ValueError(f"Expected boolean for {key}")
                facts[field] = raw[key]
        if row.max_input_tokens is not None:
            facts["max_input"] = row.max_input_tokens
        if row.max_output_tokens is not None:
            facts["max_output"] = row.max_output_tokens
        metrics = {
            "input_cost_per_token": "input_tokens",
            "output_cost_per_token": "output_tokens",
            "cache_read_input_token_cost": "cached_input",
            "cache_creation_input_token_cost": "cache_write",
        }
        prices = [
            NativePrice(metric=metric, amount=raw[key], quantity=1)
            for key, metric in metrics.items()
            if raw.get(key) is not None
        ]
        records.append(
            NormalizedRecord(
                external_id=external_id,
                name=api_id,
                canonical_id=hint,
                canonical=provider in DIRECT_MODEL_PUBLISHERS and "/" not in external_id,
                publisher_id=(
                    provider
                    if provider in DIRECT_MODEL_PUBLISHERS and "/" not in external_id
                    else None
                ),
                provider_id=provider,
                provider_name=provider,
                api_id=api_id,
                listing_kind="routing_quote" if provider == "openrouter" else "deployment",
                deployment_facts=facts,
                prices=prices,
                raw=raw,
            )
        )
    return records
