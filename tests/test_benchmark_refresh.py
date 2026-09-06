from decimal import Decimal
from uuid import uuid4

from fener.artificial_analysis import IntelligenceIndexResult
from fener.models import Model, ResearchBenchmark
from fener.private_models import BenchmarkRefresh, BenchmarkRefreshItem
from fener_worker import benchmark_jobs
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_ingestion import setup_source, write

AUTH = {"Authorization": "Bearer test-admin-key"}


def start_body():
    return {"request_id": str(uuid4()), "acknowledge_cost": True}


def current_result(*, slug="fixture-model", name="Fixture model (max)", score=Decimal("42.5")):
    return IntelligenceIndexResult(
        slug=slug,
        name=name,
        version="v4.2",
        score=score,
        estimated=False,
    )


def test_update_button_requires_auth_and_catalog_models_but_not_an_api_key(client):
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 401
    client.headers.update(AUTH)
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 409
    with Session(client.test_engine) as session:
        setup_source(session)
        write(session, "1")
        canonical = session.scalar(select(Model).where(Model.identity_status == "resolved"))
        session.add(
            Model(
                id="duplicate-name",
                identity_key="duplicate-name",
                name=canonical.name,
                family=None,
                context_window=None,
                open_weights=None,
                release_date=None,
                publisher_id=None,
                identity_status="unresolved",
            )
        )
        session.commit()
    response = client.post("/api/v1/benchmark-refresh", json=start_body())
    assert response.status_code == 202
    assert response.json()["configured"] is True
    assert response.json()["model"] == "Artificial Analysis public dataset"


def test_catalog_refresh_reads_one_current_cohort_and_imports_matching_models(client, monkeypatch):
    client.headers.update(AUTH)
    with Session(client.test_engine) as session:
        setup_source(session)
        write(session, "1")
    body = start_body()
    started = client.post("/api/v1/benchmark-refresh", json=body)
    assert started.status_code == 202
    assert started.json()["refresh"]["total_models"] == 1
    assert client.post("/api/v1/benchmark-refresh", json=body).json() == started.json()

    calls = []

    def fetch():
        calls.append(True)
        return [current_result()]

    monkeypatch.setattr(benchmark_jobs, "fetch_current_intelligence_index", fetch)
    with Session(client.test_engine) as session:
        assert benchmark_jobs.process_benchmark_refresh(session, object()) == 1
        assert benchmark_jobs.process_benchmark_refresh(session, object()) == 0
        job = session.scalar(select(BenchmarkRefresh))
        item = session.scalar(select(BenchmarkRefreshItem))
        result = session.scalar(select(ResearchBenchmark))
        assert job.status == "completed" and job.processed_models == 1
        assert item.status == "success" and item.imported_results == 1
        assert result.name == benchmark_jobs.PRIMARY_BENCHMARK
        assert result.version == "v4.2"
        assert result.score == Decimal("42.50000000")
        assert result.source_url == "https://artificialanalysis.ai/models/fixture-model"
    assert len(calls) == 1


def test_unmatched_or_unscored_models_are_no_evidence_not_failures(client, monkeypatch):
    client.headers.update(AUTH)
    with Session(client.test_engine) as session:
        setup_source(session)
        write(session, "1")
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 202
    monkeypatch.setattr(
        benchmark_jobs,
        "fetch_current_intelligence_index",
        lambda: [current_result(slug="other-model", name="Other model", score=None)],
    )

    with Session(client.test_engine) as session:
        assert benchmark_jobs.process_benchmark_refresh(session, object()) == 1
        job = session.scalar(select(BenchmarkRefresh))
        item = session.scalar(select(BenchmarkRefreshItem))
        assert item.status == "no_evidence"
        assert job.status == "completed" and job.failed_models == 0
        assert session.scalar(select(func.count()).select_from(ResearchBenchmark)) == 0


def test_source_failure_pauses_without_counting_models_and_resume_requeues_old_failures(
    client, monkeypatch
):
    client.headers.update(AUTH)
    with Session(client.test_engine) as session:
        setup_source(session)
        write(session, "1")
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 202
    monkeypatch.setattr(
        benchmark_jobs,
        "fetch_current_intelligence_index",
        lambda: (_ for _ in ()).throw(ValueError("changed page")),
    )

    with Session(client.test_engine) as session:
        assert benchmark_jobs.process_benchmark_refresh(session, object()) == 0
        job = session.scalar(select(BenchmarkRefresh))
        item = session.scalar(select(BenchmarkRefreshItem))
        assert job.status == "paused" and job.processed_models == job.failed_models == 0
        assert item.status == "queued" and item.started_at is None

        # Reproduce a result from the search-based worker that this version replaces.
        item.status = "failed"
        item.error = (
            "Research validation failed: Research provider returned HTTP 429. "
            "Check credentials, general API access and account limits. No automatic retry was made."
        )
        item.imported_results = 0
        job.processed_models = 1
        job.failed_models = 1
        session.commit()

    resumed = client.post("/api/v1/benchmark-refresh", json=start_body())
    assert resumed.status_code == 202
    assert resumed.json()["refresh"]["status"] == "queued"
    assert resumed.json()["refresh"]["processed_models"] == 0
    assert resumed.json()["refresh"]["failed_models"] == 0
    with Session(client.test_engine) as session:
        item = session.scalar(select(BenchmarkRefreshItem))
        assert item.status == "queued" and item.error is None


def test_matching_normalizes_punctuation_and_dated_api_suffixes():
    rows = [current_result(slug="o3-mini", name="o3-mini")]
    assert benchmark_jobs.match_current_result("o3-mini-2025-01-31", rows) == rows[0]
    assert benchmark_jobs.comparable_name("Gemini 3.5 Flash-Lite") == (
        benchmark_jobs.comparable_name("Gemini 3.5 Flash Lite")
    )


def test_ambiguous_source_match_is_not_selected():
    rows = [
        current_result(slug="fixture-model", name="Fixture model (max)"),
        current_result(slug="fixture-model-high", name="Fixture model"),
    ]
    assert benchmark_jobs.match_current_result("Fixture model", rows) is None
