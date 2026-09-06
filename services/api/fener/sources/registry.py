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
    "litellm": SourceSpec(
        "litellm",
        "LiteLLM",
        "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
        "https://github.com/BerriAI/litellm/blob/main/LICENSE",
        "Berri AI · MIT",
    ),
}

# Keep previously ingested evidence in the database, but never schedule, queue,
# or fetch these removed integrations.
RETIRED_SOURCES = frozenset({"openrouter", "llm_stats"})
