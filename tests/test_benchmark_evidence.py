from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fener.analytics import comparable_scores
from fener.benchmark_evidence import benchmark_metadata, safe_report_url
from fener.catalog import benchmark_groups, benchmark_results
from fener.models import BenchmarkDefinition, BenchmarkResult, SourceRecord
from fener.sources.persist import CatalogWriter
from sqlalchemy import func, select
from test_ingestion import row, setup_source


def write_benchmark(session, score, metric, tick=0):
    item = row(canonical=True)
    item.benchmarks = [
        {
            "name": "Fixture benchmark",
            "score": score,
            "metric": metric,
            "source": "https://aider.chat/docs/leaderboards/",
            "date": "2026-01-01",
        }
    ]
    item.raw["benchmarks"] = item.benchmarks
    CatalogWriter(
        session, "models_dev", datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=tick)
    ).persist(item, "models_dev", "https://models.dev/api.json")
    session.commit()


def test_units_are_separate_and_latest_confirmation_wins_without_deleting_history(session):
    setup_source(session)
    write_benchmark(session, 14, "win rate")
    write_benchmark(session, 1932, "Elo", 1)
    write_benchmark(session, 20, "win rate", 2)
    write_benchmark(session, 14, "win rate", 3)
    groups = benchmark_groups(session)
    assert {r["metric"] for r in groups} == {"Elo", "win rate"}
    assert all(r["results"] == 1 and r["comparable_results"] == 0 for r in groups)
    group = next(r for r in groups if r["metric"] == "win rate")
    result = benchmark_results(session, group_id=group["id"])[0]
    assert Decimal(result["score"]) == 14
    assert result["report_url"] == "https://aider.chat/docs/leaderboards/"
    assert result["reported_date"] == "2026-01-01"
    assert "Benchmark version not supplied" in result["quality_issues"]
    assert session.scalar(select(func.count()).select_from(BenchmarkResult)) == 3


def test_ambiguous_metadata_and_out_of_range_scores_never_become_comparable(session):
    setup_source(session)
    write_benchmark(session, 14, "win rate")
    result = session.scalar(select(BenchmarkResult))
    definition = session.get(BenchmarkDefinition, result.benchmark_id)
    record = session.get(SourceRecord, result.source_record_id)
    definition.version = "1"
    definition.score_min, definition.score_max = Decimal(0), Decimal(100)
    definition.higher_is_better = True
    result.evaluator = "Fixture evaluator v1"
    session.flush()
    assert benchmark_metadata(result, definition, record)["comparable"]
    assert comparable_scores(session)[0]
    result.score = Decimal(101)
    assert not benchmark_metadata(result, definition, record)["comparable"]
    assert comparable_scores(session)[0] == {}
    result.score = Decimal(14)
    record.raw = {
        "benchmarks": [
            {"name": definition.name, "score": 14, "metric": "Elo"},
            {"name": definition.name, "score": 14, "metric": "win rate"},
        ]
    }
    assert benchmark_metadata(result, definition, record)["metric"] == "Unspecified metric"
    assert comparable_scores(session)[0] == {}
    assert safe_report_url("javascript:alert(1)") is None
    assert safe_report_url("https://:password@aider.chat/") is None
