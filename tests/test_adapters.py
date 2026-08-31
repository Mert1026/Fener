import json
from decimal import Decimal
from pathlib import Path

from fener.sources import litellm, models_dev


def fixture(name):
    return json.loads(
        (Path(__file__).parent / "fixtures" / f"{name}.json").read_text(encoding="utf-8"),
        parse_float=Decimal,
    )


def test_models_dev_catalog_and_canonical_are_separate():
    canonical = models_dev.normalize_models(fixture("models_dev_canonical"))
    listing = models_dev.normalize(fixture("models_dev"))
    assert all(row.canonical and row.provider_id is None for row in canonical)
    assert all(not row.canonical and row.provider_id for row in listing)
    assert listing[0].prices[0].quantity == 1_000_000


def test_litellm_no_context_conflation():
    row = litellm.normalize(fixture("litellm"))[0]
    assert row.deployment_facts["max_input"] == 128000
    assert "context_window" not in row.deployment_facts
    assert row.prices[0].normalized == Decimal("2.5")


def test_missing_optional_data_is_unknown_and_extensions_are_allowed():
    rows = models_dev.normalize(
        {
            "test": {
                "id": "test",
                "name": "Test",
                "models": {"a": {"id": "a", "name": "A", "new_field": 3}},
            }
        }
    )
    assert "tool_calling" not in rows[0].deployment_facts
    assert rows[0].prices == []
