"""Read the current comparable Intelligence Index cohort from Artificial Analysis."""

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import httpx

MODELS_URL = "https://artificialanalysis.ai/models"
MAX_RESPONSE_BYTES = 5_000_000
FLIGHT_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,("(?:\\.|[^"\\])*")\]\)</script>')
VERSION = re.compile(r"Artificial Analysis Intelligence Index (v[0-9.]+)")


@dataclass(frozen=True)
class IntelligenceIndexResult:
    slug: str
    name: str
    version: str
    score: Decimal | None
    estimated: bool

    @property
    def source_url(self) -> str:
        return urljoin(MODELS_URL, f"/models/{self.slug}")

    @property
    def source_title(self) -> str:
        estimate = " (estimated)" if self.estimated else ""
        return f"{self.name}{estimate} - Artificial Analysis"


def parse_current_intelligence_index(content: bytes) -> list[IntelligenceIndexResult]:
    if not content or len(content) > MAX_RESPONSE_BYTES:
        raise ValueError("Artificial Analysis response was empty or exceeded the size limit")
    html = content.decode("utf-8")
    versions = set(VERSION.findall(html))
    if len(versions) != 1:
        raise ValueError("Artificial Analysis did not expose one current index version")
    chunks = []
    for match in FLIGHT_CHUNK.finditer(html):
        try:
            chunks.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue
    flight = "".join(chunks)
    marker = '"initialModels":'
    start = flight.find(marker)
    if start < 0:
        raise ValueError("Artificial Analysis current model dataset was not found")
    try:
        rows, _ = json.JSONDecoder().raw_decode(flight[start + len(marker) :])
    except json.JSONDecodeError as error:
        raise ValueError("Artificial Analysis current model dataset was invalid") from error
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1_000:
        raise ValueError("Artificial Analysis current model dataset had an invalid size")

    version = versions.pop()
    results = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Artificial Analysis returned an invalid model row")
        slug, name = row.get("slug"), row.get("name")
        if (
            not isinstance(slug, str)
            or not re.fullmatch(r"[a-z0-9-]+", slug)
            or not isinstance(name, str)
            or not name.strip()
            or len(name) > 500
        ):
            raise ValueError("Artificial Analysis returned an invalid model identity")
        raw_score = row.get("intelligenceIndex")
        try:
            score = Decimal(str(raw_score)) if raw_score is not None else None
        except InvalidOperation as error:
            raise ValueError("Artificial Analysis returned an invalid index score") from error
        if score is not None and (not score.is_finite() or abs(score) >= 1_000_000):
            raise ValueError("Artificial Analysis returned an out-of-range index score")
        estimated = row.get("intelligenceIndexIsEstimated")
        if type(estimated) is not bool:
            raise ValueError("Artificial Analysis omitted the score estimate status")
        results.append(
            IntelligenceIndexResult(
                slug=slug,
                name=name.strip(),
                version=version,
                score=score,
                estimated=estimated,
            )
        )
    if len({row.slug for row in results}) != len(results):
        raise ValueError("Artificial Analysis returned duplicate model variants")
    return results


def fetch_current_intelligence_index(
    client: httpx.Client | None = None,
) -> list[IntelligenceIndexResult]:
    owned = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(40, connect=10), follow_redirects=False)
    try:
        response = client.get(MODELS_URL, headers={"Accept": "text/html"})
        if response.status_code != 200:
            raise ValueError(
                f"Artificial Analysis returned HTTP {response.status_code}; no data was changed"
            )
        return parse_current_intelligence_index(response.content)
    finally:
        if owned:
            client.close()
