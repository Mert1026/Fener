import json
from decimal import Decimal

import httpx
import pytest
from fener.artificial_analysis import (
    MODELS_URL,
    fetch_current_intelligence_index,
    parse_current_intelligence_index,
)


def page(rows, version="v4.2"):
    flight = json.dumps({"initialModels": rows}, separators=(",", ":"))
    chunk = json.dumps(flight)
    return (
        f"<html>Artificial Analysis Intelligence Index {version}"
        f"<script>self.__next_f.push([1,{chunk}])</script></html>"
    ).encode()


def row(**overrides):
    return {
        "slug": "fixture-model",
        "name": "Fixture Model (max)",
        "intelligenceIndex": 42.125,
        "intelligenceIndexIsEstimated": False,
        **overrides,
    }


def test_parses_current_comparable_cohort_and_provenance():
    result = parse_current_intelligence_index(page([row()]))[0]
    assert result.version == "v4.2"
    assert result.score == Decimal("42.125")
    assert result.source_url == "https://artificialanalysis.ai/models/fixture-model"
    assert result.source_title == "Fixture Model (max) - Artificial Analysis"


def test_estimates_and_unscored_current_models_are_preserved():
    results = parse_current_intelligence_index(
        page(
            [
                row(intelligenceIndex=None),
                row(
                    slug="estimated-model",
                    name="Estimated Model",
                    intelligenceIndexIsEstimated=True,
                ),
            ]
        )
    )
    assert results[0].score is None
    assert results[1].source_title.endswith("(estimated) - Artificial Analysis")


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"<html>no dataset</html>",
        page([row()], version="v4.2") + b" Artificial Analysis Intelligence Index v4.1",
        page([row(), row()]),
        page([row(intelligenceIndex="NaN")]),
    ],
)
def test_invalid_or_ambiguous_source_data_fails_closed(content):
    with pytest.raises(ValueError):
        parse_current_intelligence_index(content)


def test_fetch_uses_only_the_fixed_public_models_page():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, content=page([row()]))

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        results = fetch_current_intelligence_index(client)
    assert results[0].score == Decimal("42.125")
    assert len(requests) == 1 and str(requests[0].url) == MODELS_URL
