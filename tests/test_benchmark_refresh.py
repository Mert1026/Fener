from datetime import timedelta
from uuid import uuid4

from fener.config import Settings, settings
from fener.db import utcnow
from fener.models import ResearchBenchmark
from fener.private_models import BenchmarkRefresh, BenchmarkRefreshItem
from fener_worker import benchmark_jobs
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_benchmark_evidence import candidate
from test_ingestion import setup_source, write

AUTH = {"Authorization": "Bearer test-admin-key"}


def start_body():
    return {"request_id": str(uuid4()), "acknowledge_cost": True}


def primary_candidate():
    return {
        **candidate(),
        "name": benchmark_jobs.PRIMARY_BENCHMARK,
        "version": "v4.2",
        "category": "general",
        "metric": benchmark_jobs.PRIMARY_BENCHMARK_METRIC,
        "evaluator": benchmark_jobs.PRIMARY_EVALUATOR,
        "source_url": "https://artificialanalysis.ai/models/fixture-model",
        "source_title": "Artificial Analysis model benchmarks",
    }


def test_primary_benchmark_filter_rejects_incompatible_results():
    row = primary_candidate()
    assert benchmark_jobs.primary_benchmark_candidate(row)
    for incompatible in (
        {**row, "name": "Coding Agent Index"},
        {**row, "version": "v4.2", "metric": "percent"},
        {**row, "evaluator": "Another evaluator"},
        {**row, "source_url": "https://example.com/copied-score"},
    ):
        assert not benchmark_jobs.primary_benchmark_candidate(incompatible)


def test_update_button_api_requires_auth_key_and_catalog_models(client, monkeypatch):
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 401
    client.headers.update(AUTH)
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 503
    monkeypatch.setattr(settings(), "zai_api_key", SecretStr("fixture-zai-never-live"))
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 409


def test_full_catalog_refresh_is_durable_and_worker_imports_without_retry(client, monkeypatch):
    monkeypatch.setattr(settings(), "zai_api_key", SecretStr("fixture-zai-never-live"))
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

    def fetch(request, key):
        calls.append(request)
        assert key == "fixture-zai-never-live"
        assert request["max_output_tokens"] == 2000
        assert request["search_domain_filter"] == "artificialanalysis.ai"
        assert "Coding Agent Index" in request["query"]
        return {"benchmark_candidates": [primary_candidate()]}

    monkeypatch.setattr(benchmark_jobs, "fetch_zai_research", fetch)
    with Session(client.test_engine) as session:
        assert (
            benchmark_jobs.process_benchmark_refresh(
                session,
                Settings(_env_file=None, zai_api_key="fixture-zai-never-live"),
            )
            == 1
        )
        assert (
            benchmark_jobs.process_benchmark_refresh(
                session,
                Settings(_env_file=None, zai_api_key="fixture-zai-never-live"),
            )
            == 0
        )
        job = session.scalar(select(BenchmarkRefresh))
        item = session.scalar(select(BenchmarkRefreshItem))
        assert job.status == "completed" and job.processed_models == 1
        assert item.status == "success" and item.imported_results == 1
        assert session.scalar(select(func.count()).select_from(ResearchBenchmark)) == 1
    assert len(calls) == 1
    status = client.get("/api/v1/benchmark-refresh").json()["refresh"]
    assert status["status"] == "completed" and status["imported_results"] == 1


def test_completed_research_without_candidates_is_not_reported_as_success(client, monkeypatch):
    monkeypatch.setattr(settings(), "zai_api_key", SecretStr("fixture-zai-never-live"))
    client.headers.update(AUTH)
    with Session(client.test_engine) as session:
        setup_source(session)
        write(session, "1")
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 202
    monkeypatch.setattr(
        benchmark_jobs, "fetch_zai_research", lambda *_: {"benchmark_candidates": []}
    )

    with Session(client.test_engine) as session:
        assert (
            benchmark_jobs.process_benchmark_refresh(
                session,
                Settings(_env_file=None, zai_api_key="fixture-zai-never-live"),
            )
            == 1
        )
        assert (
            benchmark_jobs.process_benchmark_refresh(
                session,
                Settings(_env_file=None, zai_api_key="fixture-zai-never-live"),
            )
            == 0
        )
        item = session.scalar(select(BenchmarkRefreshItem))
        assert item.status == "no_evidence"
        assert item.error == "Research completed, but no complete cited benchmark claim was found."

    view = client.get("/api/v1/benchmark-refresh").json()["refresh"]
    assert view["item_status_counts"] == {"no_evidence": 1}
    assert view["models_without_results"] == 1
    assert view["failure_reasons"] == [
        {
            "message": "Research completed, but no complete cited benchmark claim was found.",
            "count": 1,
        }
    ]


def test_worker_does_not_duplicate_a_healthy_in_flight_request(client, monkeypatch):
    monkeypatch.setattr(settings(), "zai_api_key", SecretStr("fixture-zai-never-live"))
    client.headers.update(AUTH)
    with Session(client.test_engine) as session:
        setup_source(session)
        write(session, "1")
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 202
    with Session(client.test_engine) as session:
        job = session.scalar(select(BenchmarkRefresh))
        item = session.scalar(select(BenchmarkRefreshItem))
        job.status = "running"
        item.status = "running"
        item.started_at = utcnow()
        session.commit()
        assert (
            benchmark_jobs.process_benchmark_refresh(
                session,
                Settings(_env_file=None, zai_api_key="fixture-zai-never-live"),
            )
            == 0
        )
        session.refresh(item)
        assert item.status == "running"
        assert job.processed_models == 0


def test_worker_marks_abandoned_paid_request_uncertain_without_retry(client, monkeypatch):
    monkeypatch.setattr(settings(), "zai_api_key", SecretStr("fixture-zai-never-live"))
    client.headers.update(AUTH)
    with Session(client.test_engine) as session:
        setup_source(session)
        write(session, "1")
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 202
    with Session(client.test_engine) as session:
        job = session.scalar(select(BenchmarkRefresh))
        item = session.scalar(select(BenchmarkRefreshItem))
        job.status = "running"
        item.status = "running"
        item.started_at = utcnow() - timedelta(minutes=6)
        session.commit()
        monkeypatch.setattr(
            benchmark_jobs,
            "fetch_zai_research",
            lambda *_: (_ for _ in ()).throw(AssertionError("must not retry")),
        )
        assert (
            benchmark_jobs.process_benchmark_refresh(
                session,
                Settings(_env_file=None, zai_api_key="fixture-zai-never-live"),
            )
            == 0
        )
        session.refresh(job)
        session.refresh(item)
        assert item.status == "uncertain"
        assert job.status == "completed_with_errors"
        assert job.processed_models == job.failed_models == 1


def test_blocked_refresh_resumes_after_key_is_restored(client, monkeypatch):
    monkeypatch.setattr(settings(), "zai_api_key", SecretStr("fixture-zai-never-live"))
    client.headers.update(AUTH)
    with Session(client.test_engine) as session:
        setup_source(session)
        write(session, "1")
    assert client.post("/api/v1/benchmark-refresh", json=start_body()).status_code == 202
    with Session(client.test_engine) as session:
        assert benchmark_jobs.process_benchmark_refresh(session, Settings(_env_file=None)) == 0
        job = session.scalar(select(BenchmarkRefresh))
        assert job.status == "blocked" and job.processed_models == 0
        monkeypatch.setattr(
            benchmark_jobs,
            "fetch_zai_research",
            lambda *_: {"benchmark_candidates": [primary_candidate()]},
        )
        assert (
            benchmark_jobs.process_benchmark_refresh(
                session,
                Settings(_env_file=None, zai_api_key="fixture-zai-never-live"),
            )
            == 1
        )
        assert (
            benchmark_jobs.process_benchmark_refresh(
                session,
                Settings(_env_file=None, zai_api_key="fixture-zai-never-live"),
            )
            == 0
        )
        session.refresh(job)
        assert job.status == "completed" and job.error is None
