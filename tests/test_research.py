import json
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from fener import research
from fener.config import settings
from fener.db import utcnow
from fener.models import Fact, MarketEvent, Model
from fener.private_models import ResearchRun
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

AUTH = {"Authorization": "Bearer test-admin-key"}


def payload(url="https://openai.com/index/fixture"):
    return {
        "id": "fixture-response",
        "status": "completed",
        "output": [
            {"type": "web_search_call", "status": "completed"},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Fixture finding [source].",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "start_index": 16,
                                "end_index": 24,
                                "url": url,
                                "title": "Fixture source",
                            }
                        ],
                    }
                ],
            },
        ],
        "usage": {"input_tokens": 80, "output_tokens": 20, "total_tokens": 100},
    }


@pytest.fixture
def configured(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings(), "openai_api_key", SecretStr("fixture-key-never-live"))
    monkeypatch.setattr(settings(), "fener_snapshot_dir", tmp_path / "snapshots")
    monkeypatch.setattr(settings(), "fener_research_daily_limit", 2)
    client.headers.update(AUTH)
    return client


def request_body():
    return {
        "request_id": str(uuid4()),
        "provider": "openai",
        "model": settings().fener_research_model,
        "query": "Check fixture benchmark methodology",
        "acknowledge_cost": True,
    }


def test_missing_key_and_auth_never_contact_provider(client, monkeypatch):
    monkeypatch.setattr(settings(), "openai_api_key", SecretStr(""))
    monkeypatch.setattr(research, "fetch_research", lambda *_: pytest.fail("No network allowed"))
    assert client.get("/api/v1/research").status_code == 401
    assert client.post("/api/v1/research", json=request_body()).status_code == 401
    client.headers.update(AUTH)
    assert client.get("/api/v1/research").json()["configured"] is False
    assert client.post("/api/v1/research", json=request_body()).status_code == 503
    with Session(client.test_engine) as session:
        assert session.scalar(select(func.count()).select_from(ResearchRun)) == 0


def test_approval_idempotency_limits_and_catalog_isolation(configured, monkeypatch):
    calls = []

    def fetch(request, key):
        calls.append(request)
        assert key == "fixture-key-never-live"
        return research.parse_report(payload())

    monkeypatch.setattr(research, "fetch_research", fetch)
    body = request_body()
    assert (
        configured.post("/api/v1/research", json={**body, "acknowledge_cost": False}).status_code
        == 422
    )
    created = configured.post("/api/v1/research", json=body)
    assert created.status_code == 201 and created.json()["status"] == "needs_review"
    assert configured.post("/api/v1/research", json=body).json() == created.json()
    assert (
        configured.post(
            "/api/v1/research", json={**body, "query": "A different research question"}
        ).status_code
        == 409
    )
    assert len(calls) == 1
    assert calls[0]["store"] is False
    assert calls[0]["max_tool_calls"] == 2 and calls[0]["max_output_tokens"] == 2000
    assert configured.post("/api/v1/research", json=request_body()).status_code == 201
    assert configured.post("/api/v1/research", json=request_body()).status_code == 429
    assert len(calls) == 2
    history = configured.get("/api/v1/research")
    assert "fixture-key-never-live" not in history.text
    with Session(configured.test_engine) as session:
        for table in (Fact, MarketEvent, Model):
            assert session.scalar(select(func.count()).select_from(table)) == 0
        assert "fixture-key-never-live" not in str(session.scalar(select(ResearchRun)).request)


def test_uncertain_timeout_is_recorded_and_never_retried(configured, monkeypatch):
    calls = []

    def fail(*_):
        calls.append(1)
        raise httpx.ReadTimeout("sensitive provider detail")

    monkeypatch.setattr(research, "fetch_research", fail)
    body = request_body()
    result = configured.post("/api/v1/research", json=body).json()
    assert result["status"] == "uncertain"
    assert "sensitive provider detail" not in result["error"]
    assert "charged" in result["error"]
    configured.post("/api/v1/research", json=body)
    assert len(calls) == 1


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
def test_research_requires_safe_inline_source_citations(url):
    with pytest.raises(ValueError):
        research.parse_report(payload(url))


def test_citations_and_interrupted_run_status():
    report = research.parse_report(payload())
    assert "".join(part["text"] for part in report["blocks"][0]) == "Fixture finding [source]."
    assert report["blocks"][0][1]["url"] == "https://openai.com/index/fixture"
    assert report["review_required"] is True
    row = ResearchRun(
        id=str(uuid4()),
        query="fixture",
        model="fixture",
        status="running",
        request={},
        created_at=utcnow() - timedelta(minutes=6),
    )
    assert research.run_view(row)["status"] == "uncertain"


def test_paused_features_are_unavailable_but_source_sync_remains(client, monkeypatch):
    monkeypatch.setattr(settings(), "fener_personal_features_enabled", False)
    client.headers.update(AUTH)
    for route in ("harnesses", "evaluations", "telemetry/runs"):
        assert client.get(f"/api/v1/{route}").status_code == 410
    assert client.get("/api/v1/internal/sync").status_code == 200


def test_responses_transport_uses_fixed_destination_and_does_not_retry(monkeypatch):
    original_client = httpx.Client
    requests = []

    def handler(request):
        requests.append(request)
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["Authorization"] == "Bearer fixture-not-live"
        assert json.loads(request.content) == {"store": False}
        return httpx.Response(200, json=payload())

    monkeypatch.setattr(
        research.httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    assert research.fetch_research({"store": False}, "fixture-not-live")["review_required"]
    assert len(requests) == 1

    def unavailable(request):
        requests.append(request)
        return httpx.Response(503, text="private provider error detail")

    monkeypatch.setattr(
        research.httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(unavailable), **kwargs),
    )
    with pytest.raises(ValueError, match="HTTP 503") as error:
        research.fetch_research({"store": False}, "fixture-not-live")
    assert "private provider error" not in str(error.value)
    assert len(requests) == 2
