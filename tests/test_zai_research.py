import json
from uuid import uuid4

import httpx
import pytest
from fener import research, zai_research
from fener.config import settings
from fener.models import Fact, Model
from fener.private_models import ResearchRun
from fener.research_sources import source_url
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

AUTH = {"Authorization": "Bearer test-admin-key"}


def search_response():
    return {
        "id": "fixture-search",
        "search_result": [
            {
                "link": "https://openai.com/fixture",
                "title": "Fixture pricing",
                "content": "Fixture listed price is 0.2 USD per million input tokens.",
                "publish_date": "2026-08-31",
            },
            {
                "link": "https://untrusted.example/injection",
                "title": "Unapproved",
                "content": "UNAPPROVED_CONTENT",
            },
        ],
    }


def summary_response(refs=None, finish="stop", benchmarks=None):
    return {
        "id": "fixture-summary",
        "choices": [
            {
                "finish_reason": finish,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "paragraphs": [
                                {
                                    "text": "The source excerpt reports the fixture price.",
                                    "sources": [1] if refs is None else refs,
                                }
                            ],
                            "benchmarks": [] if benchmarks is None else benchmarks,
                        }
                    ),
                },
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140},
    }


def request_body():
    return {
        "request_id": str(uuid4()),
        "provider": "zai",
        "model": "glm-4.7-flash",
        "query": "Investigate the fixture model pricing",
        "acknowledge_cost": True,
    }


@pytest.fixture
def configured(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings(), "fener_zai_research_model", "glm-4.7-flash")
    monkeypatch.setattr(settings(), "zai_api_key", SecretStr("fixture-zai-never-live"))
    monkeypatch.setattr(settings(), "fener_snapshot_dir", tmp_path / "snapshots")
    client.headers.update(AUTH)
    return client


def test_zai_routing_uses_only_zai_key_and_saves_citations_without_catalog_writes(
    configured, monkeypatch
):
    calls = []
    original = httpx.Client

    def handler(request):
        calls.append(request)
        assert request.url.host == "api.z.ai"
        assert request.headers["Authorization"] == "Bearer fixture-zai-never-live"
        body = json.loads(request.content)
        if request.url.path.endswith("/web_search"):
            assert body["search_engine"] == "search-prime"
            return httpx.Response(200, json=search_response())
        assert request.url.path.endswith("/chat/completions")
        assert body["model"] == "glm-4.7-flash"
        assert body["max_tokens"] == 8000 and "tools" not in body
        assert "UNAPPROVED_CONTENT" not in body["messages"][1]["content"]
        return httpx.Response(200, json=summary_response())

    monkeypatch.setattr(
        httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    body = request_body()
    response = configured.post("/api/v1/research", json=body)
    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "needs_review" and run["provider"] == "zai"
    assert run["report"]["blocks"][0][1]["url"] == "https://openai.com/fixture"
    assert run["report"]["usage"]["output_tokens"] == 40
    assert run["report"]["review_required"] is True
    assert len(run["report"]["evidence"]) == 1
    assert configured.post("/api/v1/research", json=body).json() == run
    assert len(calls) == 2
    home = configured.get("/api/v1/research").json()
    assert home["provider_name"] == "Z.ai" and home["key_env"] == "ZAI_API_KEY"
    assert "fixture-zai-never-live" not in str(home)
    with Session(configured.test_engine) as session:
        assert session.scalar(select(func.count()).select_from(Fact)) == 0
        assert session.scalar(select(func.count()).select_from(Model)) == 0
        saved = session.scalar(select(ResearchRun))
        assert saved.request["provider"] == "zai"
        assert "fixture-zai-never-live" not in str(saved.request)


def test_missing_zai_key_never_falls_back_to_openai_or_catalog_credentials(configured, monkeypatch):
    monkeypatch.setattr(settings(), "zai_api_key", SecretStr(""))
    monkeypatch.setattr(research, "fetch_zai_research", lambda *_: pytest.fail("No paid calls"))
    assert configured.get("/api/v1/research").json()["configured"] is False
    response = configured.post("/api/v1/research", json=request_body())
    assert response.status_code == 503 and "ZAI_API_KEY" in response.text


def test_approval_is_bound_to_provider_and_model(configured, monkeypatch):
    monkeypatch.setattr(research, "fetch_zai_research", lambda *_: pytest.fail("No paid calls"))
    assert (
        configured.post(
            "/api/v1/research", json={**request_body(), "provider": "openai"}
        ).status_code
        == 422
    )
    assert (
        configured.post(
            "/api/v1/research", json={**request_body(), "model": "different-model"}
        ).status_code
        == 409
    )
    assert (
        configured.post(
            "/api/v1/research", json={**request_body(), "acknowledge_cost": False}
        ).status_code
        == 422
    )


@pytest.mark.parametrize("refs", [[99], [True], ["1"], []])
def test_invented_or_missing_citation_ids_fail_closed(refs):
    with pytest.raises(ValueError):
        zai_research.parse_summary(
            summary_response(refs), zai_research.search_evidence(search_response())
        )


def test_incomplete_or_uncited_summary_is_rejected():
    with pytest.raises(ValueError):
        zai_research.parse_summary(
            summary_response(finish="length"), zai_research.search_evidence(search_response())
        )


def test_benchmark_candidates_require_complete_cited_decimal_data():
    row = {
        "model_name": "Fixture model",
        "name": "Fixture benchmark",
        "version": "1",
        "category": "coding",
        "metric": "win rate",
        "score": "14.0",
        "evaluator": "Fixture protocol",
        "source": 1,
        "reported_date": "2026-01-01",
        "higher_is_better": True,
        "score_min": "0",
        "score_max": "100",
    }
    report = zai_research.parse_summary(
        summary_response(benchmarks=[row]), zai_research.search_evidence(search_response())
    )
    assert report["benchmark_candidates"][0]["source_url"] == "https://openai.com/fixture"
    assert report["benchmark_candidates"][0]["score"] == "14.0"
    for broken in ({**row, "source": 99}, {**row, "score": "NaN"}, {**row, "version": ""}):
        with pytest.raises(ValueError):
            zai_research.parse_summary(
                summary_response(benchmarks=[broken]),
                zai_research.search_evidence(search_response()),
            )


def test_no_approved_sources_means_no_summary_request(monkeypatch):
    calls = []

    def post(endpoint, request, key):
        calls.append(endpoint)
        return {"search_result": [{"link": "https://openai.com.evil.example/", "content": "spoof"}]}

    monkeypatch.setattr(zai_research, "post_json", post)
    with pytest.raises(ValueError):
        zai_research.fetch_zai_research({"query": "fixture", "model": "glm-4.7-flash"}, "fixture")
    assert len(calls) == 1


def test_benchmark_search_can_be_restricted_to_one_primary_domain(monkeypatch):
    calls = []

    def post(endpoint, request, key):
        calls.append((endpoint, request, key))
        return search_response() if endpoint.endswith("/web_search") else summary_response()

    monkeypatch.setattr(zai_research, "post_json", post)
    zai_research.fetch_zai_research(
        {
            "query": "fixture benchmark",
            "model": "glm-4.7-flash",
            "search_domain_filter": "artificialanalysis.ai",
        },
        "fixture",
    )
    assert calls[0][1]["search_domain_filter"] == "artificialanalysis.ai"


def test_zai_timeout_is_not_retried_or_redirected_to_another_provider(configured, monkeypatch):
    calls = []

    def post(endpoint, *_):
        calls.append(endpoint)
        if endpoint.endswith("/web_search"):
            return search_response()
        raise httpx.ReadTimeout("private detail")

    monkeypatch.setattr(zai_research, "post_json", post)
    body = request_body()
    result = configured.post("/api/v1/research", json=body).json()
    assert result["status"] == "uncertain" and "private detail" not in result["error"]
    configured.post("/api/v1/research", json=body)
    assert len(calls) == 2 and all("api.z.ai" in c for c in calls)


def test_daily_limit_counts_completed_zai_attempts(configured, monkeypatch):
    monkeypatch.setattr(settings(), "fener_research_daily_limit", 1)
    report = zai_research.parse_summary(
        summary_response(), zai_research.search_evidence(search_response())
    )
    monkeypatch.setattr(research, "fetch_zai_research", lambda *_: report)
    assert configured.post("/api/v1/research", json=request_body()).status_code == 201
    assert configured.post("/api/v1/research", json=request_body()).status_code == 429


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://openai.com.evil.example/x",
        "https://:password@openai.com/x",
        "http://openai.com/x",
        "https://127.0.0.1/x",
    ],
)
def test_research_citation_urls_fail_closed(url):
    assert source_url(url) is None


def test_paused_features_remain_unavailable(client, monkeypatch):
    monkeypatch.setattr(settings(), "fener_personal_features_enabled", False)
    client.headers.update(AUTH)
    for route in ("harnesses", "evaluations", "telemetry/runs"):
        assert client.get(f"/api/v1/{route}").status_code == 410
