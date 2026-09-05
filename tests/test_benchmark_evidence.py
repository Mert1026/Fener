from fener.ai_benchmarks import persist_research_benchmarks
from fener.analytics import comparable_scores
from fener.catalog import benchmark_groups, benchmark_results
from fener.evidence import digest
from fener.models import (
    BenchmarkDefinition,
    BenchmarkResult,
    Model,
    ResearchBenchmark,
    SourceRecord,
)
from fener.private_models import ResearchRun
from sqlalchemy import func, select
from test_ingestion import setup_source, write


def candidate(model_name="Fixture model"):
    return {
        "model_name": model_name,
        "name": "Fixture benchmark",
        "version": "2026-01",
        "category": "coding",
        "metric": "win rate",
        "score": "14",
        "evaluator": "Fixture protocol",
        "source_url": "https://aider.chat/docs/leaderboards/",
        "source_title": "Fixture report",
        "reported_date": "2026-01-01",
        "higher_is_better": True,
        "score_min": "0",
        "score_max": "100",
    }


def research_run(session):
    row = ResearchRun(
        id="00000000-0000-0000-0000-000000000001",
        query="fixture benchmark research",
        model="glm-4.7-flash",
        status="needs_review",
        request={"provider": "zai"},
    )
    session.add(row)
    session.commit()
    return row


def test_benchmark_api_uses_only_cited_ai_extractions(session):
    setup_source(session)
    write(session, "1")
    model = session.scalar(select(Model))
    record = session.scalar(select(SourceRecord))
    assert model is not None and record is not None
    definition = BenchmarkDefinition(
        id=digest("legacy benchmark", "1"),
        name="Legacy benchmark",
        version="1",
        category="legacy",
        source_record_id=record.id,
    )
    session.add(definition)
    session.flush()
    session.add(
        BenchmarkResult(
            id=digest("legacy result"),
            model_id=model.id,
            benchmark_id=definition.id,
            score=99,
            verification="aggregated",
            evaluator="Legacy catalog",
            source_record_id=record.id,
        )
    )
    session.commit()
    run = research_run(session)
    result = persist_research_benchmarks(session, [candidate()], research_run_id=run.id)
    session.commit()
    assert result == {"imported": 1, "skipped": []}
    groups = benchmark_groups(session)
    assert groups[0]["metric"] == "win rate" and groups[0]["results"] == 1
    assert groups[0]["version"] == "2026-01"
    assert groups[0]["evaluator"] == "Fixture protocol"
    row = benchmark_results(session, group_id=groups[0]["id"])[0]
    assert row["name"] != "Legacy benchmark"
    assert row["score"] == "14.00000000"
    assert row["source"] == "AI benchmark research"
    assert row["report_url"] == "https://aider.chat/docs/leaderboards/"
    assert row["source_title"] == "Fixture report"
    assert row["verification"] == "ai_extracted_unverified"
    assert row["comparable"] is True
    assert "AI-extracted result" in row["quality_issues"][0]
    assert comparable_scores(session) == ({}, [])


def test_benchmark_cohorts_never_mix_versions_or_evaluators(session):
    setup_source(session)
    write(session, "1")
    run = research_run(session)
    persist_research_benchmarks(
        session,
        [
            candidate(),
            {**candidate(), "version": "2026-02"},
            {**candidate(), "evaluator": "Different protocol"},
        ],
        research_run_id=run.id,
    )
    session.commit()

    groups = benchmark_groups(session)
    assert len(groups) == 3
    assert len({group["id"] for group in groups}) == 3
    assert all(group["models"] == 1 and group["results"] == 1 for group in groups)


def test_benchmark_without_a_documented_scale_is_not_comparable(session):
    setup_source(session)
    write(session, "1")
    run = research_run(session)
    persist_research_benchmarks(
        session,
        [{**candidate(), "score_min": None, "score_max": None}],
        research_run_id=run.id,
    )
    session.commit()

    row = benchmark_results(session)[0]
    assert row["comparable"] is False
    assert "Documented numeric scale not supplied" in row["quality_issues"]


def test_ai_benchmark_requires_unique_exact_catalog_model_name(session):
    setup_source(session)
    write(session, "1")
    run = research_run(session)
    result = persist_research_benchmarks(
        session, [candidate("Unknown model")], research_run_id=run.id
    )
    session.commit()
    assert result["imported"] == 0
    assert result["skipped"][0]["reason"] == "No unique exact catalog model-name match"
    assert session.scalar(select(func.count()).select_from(ResearchBenchmark)) == 0
