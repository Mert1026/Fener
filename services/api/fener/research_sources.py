"""Approved citation domains shared by research providers."""

from typing import Any
from urllib.parse import urlsplit

DOMAINS = [
    "openai.com",
    "anthropic.com",
    "deepmind.google",
    "ai.google.dev",
    "blog.google",
    "ai.meta.com",
    "mistral.ai",
    "deepseek.com",
    "qwenlm.github.io",
    "x.ai",
    "cohere.com",
    "artificialanalysis.ai",
    "aider.chat",
    "livebench.ai",
    "llm-stats.com",
    "openrouter.ai",
    "models.dev",
    "z.ai",
]


def source_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme == "https"
            and parsed.username is None
            and parsed.port in {None, 443}
            and any(host == domain or host.endswith("." + domain) for domain in DOMAINS)
        ):
            return value
    except ValueError:
        pass
    return None
