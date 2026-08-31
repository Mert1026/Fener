from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpec:
    id: str
    name: str
    url: str
    terms_url: str
    attribution: str


SOURCES = {
    "models_dev": SourceSpec(
        "models_dev",
        "models.dev",
        "https://models.dev/api.json",
        "https://github.com/anomalyco/models.dev/blob/dev/LICENSE",
        "models.dev contributors · MIT",
    ),
    "openrouter": SourceSpec(
        "openrouter",
        "OpenRouter",
        "https://openrouter.ai/api/v1/models",
        "https://openrouter.ai/terms",
        "OpenRouter · provider marketplace data",
    ),
    "litellm": SourceSpec(
        "litellm",
        "LiteLLM",
        "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
        "https://github.com/BerriAI/litellm/blob/main/LICENSE",
        "Berri AI · MIT",
    ),
    "llm_stats": SourceSpec(
        "llm_stats",
        "LLM Stats",
        "https://api.zeroeval.com/stats/v1/models",
        "https://llm-stats.com/legal/terms-of-service",
        "LLM Stats · https://llm-stats.com",
    ),
}
